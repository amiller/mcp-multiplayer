#!/usr/bin/env python3
"""
MCP Multiplayer Server - FastMCP server providing multiplayer channel tools
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dotenv import load_dotenv

from fastmcp import FastMCP
from fastmcp.server.context import request_ctx
from channel_manager import ChannelManager
from bot_manager import BotManager, BotDefinition

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global managers
channel_manager = ChannelManager()
bot_manager = BotManager(channel_manager)

# Create FastMCP instance
mcp = FastMCP("Multiplayer Channels")

def get_session_id():
    """Get session ID from FastMCP context (client-provided)."""
    try:
        ctx = request_ctx.get()
        if hasattr(ctx, 'request') and ctx.request:
            # Use the session ID that Claude provides
            session_id = ctx.request.headers.get('Mcp-Session-Id')
            if session_id:
                return session_id
    except:
        pass

    # Fallback to None - let FastMCP handle session management
    return None

@mcp.tool()
def health_check() -> str:
    """Check if the multiplayer server is healthy."""
    return f"Multiplayer server healthy at {datetime.utcnow().isoformat()}"

@mcp.tool()
def create_channel(name: str, slots: List[str], bots: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Create a new multiplayer channel with specified slots.

    Args:
        name: Channel name
        slots: List of slot types like ["bot:guess-referee", "invite:player1", "invite:player2"]
        bots: Optional list of bot definitions. Each bot dict has:
            - name: Bot name
            - version: Bot version (default "1.0")
            - code_ref: Reference like "builtin://GuessBot" OR
            - inline_code: Python code defining bot class with:
                * __init__(self, ctx, params): Initialize
                * on_init(): Called when bot attaches
                * on_join(player_id): Called when player joins
                * on_message(msg): Called on new messages
                * self.ctx.post(kind, body): Post messages
            - manifest: Dict with summary, hooks ["on_init", "on_join", "on_message"], emits, params

    Returns:
        Channel creation result with channel_id and invite codes
    """
    try:
        if not name or not slots:
            raise ValueError("name and slots required")

        if bots is None:
            bots = []

        # Create channel
        result = channel_manager.create_channel(name, slots, bots)

        # Attach bots if provided
        for bot_spec in bots:
            try:
                bot_def = BotDefinition(
                    name=bot_spec["name"],
                    version=bot_spec.get("version", "1.0"),
                    code_ref=bot_spec.get("code_ref"),
                    inline_code=bot_spec.get("inline_code"),
                    manifest=bot_spec.get("manifest"),
                    env_redacted=bot_spec.get("env_redacted")
                )
                bot_manager.attach_bot(result["channel_id"], bot_def)
            except Exception as e:
                logger.error(f"Failed to attach bot {bot_spec.get('name')}: {e}")

        return result

    except ValueError as e:
        raise ValueError(f"INVALID_REQUEST: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating channel: {e}")
        raise ValueError(f"INTERNAL_ERROR: Failed to create channel")

@mcp.tool()
def join_channel(invite_code: str) -> Dict[str, Any]:
    """
    Join a multiplayer channel using an invite code.

    Args:
        invite_code: The invite code for the channel (e.g., "inv_...")

    Returns:
        Join result with channel info and user slot assignment
    """
    try:
        if not invite_code:
            raise ValueError("invite_code required")

        session_id = get_session_id()
        if not session_id:
            raise ValueError("NO_SESSION: Missing session ID from client")

        result = channel_manager.join_channel(invite_code, session_id)

        # Notify bots of the join
        bot_manager.dispatch_join(result["channel_id"], session_id)

        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f"Error joining channel: {e}")
        raise ValueError(f"INTERNAL_ERROR: Failed to join channel")

@mcp.tool(exclude_args=["body"])
def post_message(channel_id: str, kind: str = "user", body = None) -> Dict[str, Any]:
    """
    Post a message to a multiplayer channel.

    Args:
        channel_id: The channel ID (e.g., "chn_...")
        kind: Message type, defaults to "user"
        body: Message content as a dictionary or string

    Returns:
        Message posting result with message ID and timestamp
    """
    try:
        if not channel_id:
            raise ValueError("channel_id required")

        if body is None:
            body_dict = {}
        elif isinstance(body, str):
            body_dict = {"text": body}
        elif isinstance(body, dict):
            body_dict = body
        else:
            raise ValueError(f"Invalid body type: {type(body)}")

        session_id = get_session_id()
        if not session_id:
            raise ValueError("NO_SESSION: Missing session ID from client")

        result = channel_manager.post_message(channel_id, session_id, kind, body_dict)

        # Dispatch message to bots
        message = {
            "id": result["msg_id"],
            "channel_id": channel_id,
            "sender": session_id,
            "kind": kind,
            "body": body_dict,
            "ts": result["ts"]
        }
        bot_manager.dispatch_message(channel_id, message)

        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f"Error posting message: {e}")
        raise ValueError(f"INTERNAL_ERROR: Failed to post message")

@mcp.tool()
def make_game_move(channel_id: str, game: str, action: str, value: int) -> Dict[str, Any]:
    """
    Make a game move (like guessing in a guessing game).

    Args:
        channel_id: The channel ID
        game: Game type (e.g., "guess")
        action: Move action (e.g., "guess", "concede")
        value: The move value (e.g., guessed number)

    Returns:
        Message posting result
    """
    try:
        move_body = {
            "type": "move",
            "game": game,
            "action": action,
            "value": value
        }

        session_id = get_session_id()
        if not session_id:
            raise ValueError("NO_SESSION: Missing session ID from client")

        result = channel_manager.post_message(channel_id, session_id, "user", move_body)

        # Dispatch message to bots
        message = {
            "id": result["msg_id"],
            "channel_id": channel_id,
            "sender": session_id,
            "kind": "user",
            "body": move_body,
            "ts": result["ts"]
        }
        bot_manager.dispatch_message(channel_id, message)

        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f"Error making game move: {e}")
        raise ValueError(f"INTERNAL_ERROR: Failed to make game move")

@mcp.tool()
def sync_messages(channel_id: str, cursor: Optional[int] = None, timeout_ms: int = 25000) -> Dict[str, Any]:
    """
    Get messages from a channel since cursor.

    Args:
        channel_id: The channel ID
        cursor: Optional last seen message ID
        timeout_ms: Long-poll timeout in milliseconds

    Returns:
        Messages and sync info
    """
    try:
        if not channel_id:
            raise ValueError("channel_id required")

        session_id = get_session_id()
        if not session_id:
            raise ValueError("NO_SESSION: Missing session ID from client")

        result = channel_manager.sync_messages(
            channel_id, session_id, cursor, timeout_ms
        )

        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f"Error syncing messages: {e}")
        raise ValueError(f"INTERNAL_ERROR: Failed to sync messages")

@mcp.tool()
def get_channel_info(channel_id: str) -> Dict[str, Any]:
    """
    Get current channel information and member list.

    Args:
        channel_id: The channel ID

    Returns:
        Channel view with members and bots
    """
    try:
        if not channel_id:
            raise ValueError("channel_id required")

        session_id = get_session_id()
        if not session_id:
            raise ValueError("NO_SESSION: Missing session ID from client")

        # Check membership
        if not channel_manager._is_member(channel_id, session_id):
            raise ValueError("NOT_MEMBER: Not a channel member")

        view = channel_manager._get_channel_view(channel_id)
        bots = bot_manager.get_channel_bots(channel_id)

        result = {
            "view": view.__dict__,
            "bots": bots
        }

        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f"Error getting channel info: {e}")
        raise ValueError(f"INTERNAL_ERROR: Failed to get channel info")

@mcp.tool()
def list_channels() -> Dict[str, Any]:
    """
    List all available channels (debug endpoint).

    Returns:
        List of all channels with basic info
    """
    channels = []
    for channel_id, channel in channel_manager.channels.items():
        channels.append({
            "channel_id": channel_id,
            "name": channel["name"],
            "slots": [slot.__dict__ for slot in channel["slots"]],
            "message_count": len(channel["messages"]),
            "bots": list(bot_manager.bot_instances.get(channel_id, {}).keys())
        })

    return {
        "channels": channels,
        "total_channels": len(channels)
    }

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "9201"))

    logger.info(f"Starting Multiplayer MCP server on {host}:{port}")
    mcp.run(transport="streamable-http", host=host, port=port)