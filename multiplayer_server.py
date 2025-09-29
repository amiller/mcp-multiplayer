#!/usr/bin/env python3
"""
MCP Multiplayer Server - FastMCP server providing multiplayer channel tools
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
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

# Simple session tracking for demo (in production, would use OAuth)
session_store = {}

def get_session_id():
    """Get session ID from request context headers or generate one."""
    try:
        # Try to get session ID from request context (set by OAuth proxy)
        ctx = request_ctx.get()
        if hasattr(ctx, 'request') and ctx.request and hasattr(ctx.request, 'headers'):
            session_id = ctx.request.headers.get('X-Session-ID')
            if session_id:
                return session_id
    except:
        pass  # Fall back to generating session ID

    # Generate new session ID as fallback
    import secrets
    session_id = f"sess_{secrets.token_urlsafe(8)}"
    session_store[session_id] = {"created_at": datetime.utcnow().isoformat()}
    return session_id

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
        bots: Optional list of bot definitions to attach

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

        result = channel_manager.join_channel(invite_code, session_id)

        # Notify bots of the join
        bot_manager.dispatch_join(result["channel_id"], session_id)

        return result

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f"Error joining channel: {e}")
        raise ValueError(f"INTERNAL_ERROR: Failed to join channel")

@mcp.tool()
def post_message(channel_id: str, kind: str = "user", body: Optional[str] = None) -> Dict[str, Any]:
    """
    Post a message to a multiplayer channel.

    Args:
        channel_id: The channel ID (e.g., "chn_...")
        kind: Message type, defaults to "user"
        body: Message content as a dictionary

    Returns:
        Message posting result with message ID and timestamp
    """
    try:
        if not channel_id:
            raise ValueError("channel_id required")

        if body is None:
            body_dict = {}
        else:
            # Convert string message to dictionary format expected by channel_manager
            body_dict = {"text": body}

        session_id = get_session_id()

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