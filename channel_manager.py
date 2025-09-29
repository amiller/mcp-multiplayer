#!/usr/bin/env python3
"""
Channel Manager - Core channel operations for MCP Multiplayer
"""

import json
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import secrets

@dataclass
class Slot:
    slot_id: str
    kind: str  # "bot" or "invite"
    label: str
    filled_by: Optional[str] = None  # session_id or "bot:BotName"
    admin: bool = False

@dataclass
class Message:
    id: int
    channel_id: str
    sender: str  # session_id or "bot:BotName" or "system"
    kind: str  # "user", "bot", "system", "control"
    body: Dict[str, Any]
    ts: str

@dataclass
class ChannelView:
    channel_id: str
    name: str
    slots: List[Dict[str, Any]]
    created_at: str

class ChannelManager:
    def __init__(self):
        self.channels: Dict[str, Dict] = {}
        self.invites: Dict[str, Dict] = {}  # invite_code -> {channel_id, slot_id}
        self.session_slots: Dict[str, Dict] = {}  # session_id -> {channel_id, slot_id}
        self.message_counter = 0
        self.lock = threading.RLock()

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{secrets.token_urlsafe(8)}"

    def _generate_invite_code(self) -> str:
        return f"inv_{secrets.token_urlsafe(16)}"

    def _next_message_id(self) -> int:
        with self.lock:
            self.message_counter += 1
            return self.message_counter

    def create_channel(self, name: str, slots: List[str], bots: List[Dict] = None) -> Dict:
        """
        Create a new channel with specified slots.

        Args:
            name: Channel name
            slots: List like ["bot:guess-referee", "invite:player", "invite:player"]
            bots: List of BotDef for bot slots

        Returns:
            {channel_id, invites: [invite_code...], view: ChannelView}
        """
        with self.lock:
            channel_id = self._generate_id("chn")

            # Parse slots and create slot objects
            slot_objects = []
            invite_codes = []

            for i, slot_spec in enumerate(slots):
                slot_id = f"s{i}"
                parts = slot_spec.split(":", 1)
                kind = parts[0]
                label = parts[1] if len(parts) > 1 else f"{kind}_{i}"

                slot = Slot(
                    slot_id=slot_id,
                    kind=kind,
                    label=label,
                    admin=(kind == "bot")  # Bots are admin by default
                )

                if kind == "invite":
                    # Generate invite code for this slot
                    invite_code = self._generate_invite_code()
                    invite_codes.append(invite_code)
                    self.invites[invite_code] = {
                        "channel_id": channel_id,
                        "slot_id": slot_id
                    }
                elif kind == "bot" and bots:
                    # Find matching bot for this slot
                    bot_def = next((b for b in bots if b.get("slot") == slot_spec), None)
                    if bot_def:
                        slot.filled_by = f"bot:{bot_def['name']}"

                slot_objects.append(slot)

            # Create channel
            channel = {
                "channel_id": channel_id,
                "name": name,
                "slots": slot_objects,
                "messages": [],
                "bots": {},
                "created_at": datetime.utcnow().isoformat()
            }

            self.channels[channel_id] = channel

            # Post system message about bots if any
            if bots:
                self._post_system_message(channel_id, {
                    "type": "bots_announced",
                    "bots": [{
                        "slot_id": slot.slot_id,
                        "name": bot["name"],
                        "version": bot.get("version", "1.0"),
                        "summary": bot.get("manifest", {}).get("summary", "")
                    } for slot, bot in zip(slot_objects, bots) if slot.kind == "bot"]
                })

            return {
                "channel_id": channel_id,
                "invites": invite_codes,
                "view": self._get_channel_view(channel_id)
            }

    def join_channel(self, invite_code: str, session_id: str) -> Dict:
        """
        Join a channel using an invite code.

        Returns:
            {channel_id, slot_id, view: ChannelView}
        """
        with self.lock:
            if invite_code not in self.invites:
                raise ValueError("INVITE_INVALID")

            invite_info = self.invites[invite_code]
            channel_id = invite_info["channel_id"]
            slot_id = invite_info["slot_id"]

            if channel_id not in self.channels:
                raise ValueError("CHANNEL_NOT_FOUND")

            channel = self.channels[channel_id]
            slot = next((s for s in channel["slots"] if s.slot_id == slot_id), None)

            if not slot:
                raise ValueError("SLOT_NOT_FOUND")

            if slot.filled_by is not None:
                # Check if it's the same session (idempotent)
                if slot.filled_by == session_id:
                    return {
                        "channel_id": channel_id,
                        "slot_id": slot_id,
                        "view": self._get_channel_view(channel_id)
                    }
                else:
                    raise ValueError("SLOT_ALREADY_FILLED")

            # Bind session to slot
            slot.filled_by = session_id
            self.session_slots[session_id] = {
                "channel_id": channel_id,
                "slot_id": slot_id
            }

            # Remove the invite code (one-time use)
            del self.invites[invite_code]

            return {
                "channel_id": channel_id,
                "slot_id": slot_id,
                "view": self._get_channel_view(channel_id)
            }

    def post_message(self, channel_id: str, session_id: str, kind: str, body: Dict[str, Any]) -> Dict:
        """
        Post a message to a channel.

        Returns:
            {msg_id, ts}
        """
        with self.lock:
            if channel_id not in self.channels:
                raise ValueError("CHANNEL_NOT_FOUND")

            # Check if session is a member
            if not self._is_member(channel_id, session_id):
                raise ValueError("NOT_MEMBER")

            msg_id = self._next_message_id()
            ts = datetime.utcnow().isoformat()

            message = Message(
                id=msg_id,
                channel_id=channel_id,
                sender=session_id,
                kind=kind,
                body=body,
                ts=ts
            )

            self.channels[channel_id]["messages"].append(message)

            return {"msg_id": msg_id, "ts": ts}

    def sync_messages(self, channel_id: str, session_id: str, cursor: Optional[int] = None,
                     timeout_ms: int = 25000) -> Dict:
        """
        Get messages since cursor with optional long-polling.

        Returns:
            {messages: [Message], cursor: int, view: ChannelView | null}
        """
        with self.lock:
            if channel_id not in self.channels:
                raise ValueError("CHANNEL_NOT_FOUND")

            if not self._is_member(channel_id, session_id):
                raise ValueError("NOT_MEMBER")

            channel = self.channels[channel_id]
            messages = channel["messages"]

            if cursor is None:
                cursor = 0

            # Get new messages
            new_messages = [msg for msg in messages if msg.id > cursor]

            # If no new messages and timeout requested, implement simple polling
            if not new_messages and timeout_ms > 0:
                # For now, just return empty (real implementation would use threading.Event)
                pass

            # Determine new cursor
            new_cursor = max((msg.id for msg in messages), default=cursor)

            # Include view if channel composition changed (simplified check)
            view = self._get_channel_view(channel_id) if not new_messages else None

            return {
                "messages": [asdict(msg) for msg in new_messages],
                "cursor": new_cursor,
                "view": asdict(view) if view else None
            }

    def update_channel(self, channel_id: str, session_id: str, ops: List[Dict]) -> Dict:
        """
        Update channel (admin only).

        Returns:
            {ok: bool, view: ChannelView}
        """
        with self.lock:
            if channel_id not in self.channels:
                raise ValueError("CHANNEL_NOT_FOUND")

            if not self._is_admin(channel_id, session_id):
                raise ValueError("NOT_ADMIN")

            channel = self.channels[channel_id]

            for op in ops:
                op_type = op.get("type")

                if op_type == "set_bot":
                    self._op_set_bot(channel, op)
                elif op_type == "remove_bot":
                    self._op_remove_bot(channel, op)
                elif op_type == "yield_slot":
                    self._op_yield_slot(channel, op)
                elif op_type == "set_admin":
                    self._op_set_admin(channel, op)
                elif op_type == "rename":
                    channel["name"] = op["name"]
                else:
                    raise ValueError(f"BAD_OP: {op_type}")

                # Post system message for the change
                self._post_system_message(channel_id, {
                    "type": f"{op_type}_applied",
                    "op": op
                })

            return {
                "ok": True,
                "view": self._get_channel_view(channel_id)
            }

    def _is_member(self, channel_id: str, session_id: str) -> bool:
        """Check if session is a member of the channel."""
        channel = self.channels.get(channel_id)
        if not channel:
            return False

        # Allow bot senders (format: "bot:bot_id" or "bot:BotName")
        if session_id.startswith("bot:"):
            # Check if any bot slot matches this bot
            return any(slot.filled_by and (
                slot.filled_by == session_id or
                slot.filled_by.startswith("bot:")
            ) for slot in channel["slots"])

        return any(slot.filled_by == session_id for slot in channel["slots"])

    def _is_admin(self, channel_id: str, session_id: str) -> bool:
        """Check if session has admin privileges."""
        channel = self.channels.get(channel_id)
        if not channel:
            return False

        return any(slot.filled_by == session_id and slot.admin
                  for slot in channel["slots"])

    def _get_channel_view(self, channel_id: str) -> ChannelView:
        """Get channel view for external consumption."""
        channel = self.channels[channel_id]

        return ChannelView(
            channel_id=channel_id,
            name=channel["name"],
            slots=[asdict(slot) for slot in channel["slots"]],
            created_at=channel["created_at"]
        )

    def _post_system_message(self, channel_id: str, body: Dict[str, Any]):
        """Post a system message."""
        msg_id = self._next_message_id()
        ts = datetime.utcnow().isoformat()

        message = Message(
            id=msg_id,
            channel_id=channel_id,
            sender="system",
            kind="system",
            body=body,
            ts=ts
        )

        self.channels[channel_id]["messages"].append(message)

    def _op_set_bot(self, channel: Dict, op: Dict):
        """Handle set_bot operation."""
        slot_id = op["slot_id"]
        bot_def = op["bot_def"]

        slot = next((s for s in channel["slots"] if s.slot_id == slot_id), None)
        if not slot:
            raise ValueError("SLOT_NOT_FOUND")

        slot.kind = "bot"
        slot.filled_by = f"bot:{bot_def['name']}"
        slot.admin = True

    def _op_remove_bot(self, channel: Dict, op: Dict):
        """Handle remove_bot operation."""
        slot_id = op["slot_id"]

        slot = next((s for s in channel["slots"] if s.slot_id == slot_id), None)
        if not slot:
            raise ValueError("SLOT_NOT_FOUND")

        slot.filled_by = None
        if slot.kind == "bot":
            slot.admin = False

    def _op_yield_slot(self, channel: Dict, op: Dict):
        """Handle yield_slot operation."""
        slot_id = op["slot_id"]
        to_kind = op["to"]

        slot = next((s for s in channel["slots"] if s.slot_id == slot_id), None)
        if not slot:
            raise ValueError("SLOT_NOT_FOUND")

        slot.kind = to_kind
        slot.filled_by = None
        slot.admin = (to_kind == "bot")

    def _op_set_admin(self, channel: Dict, op: Dict):
        """Handle set_admin operation."""
        slot_id = op["slot_id"]
        admin = op["admin"]

        slot = next((s for s in channel["slots"] if s.slot_id == slot_id), None)
        if not slot:
            raise ValueError("SLOT_NOT_FOUND")

        slot.admin = admin