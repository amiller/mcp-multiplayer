#!/usr/bin/env python3
"""
Test MCP session handling through OAuth proxy
"""

import sys
import os

# Add the scripts directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import MCPClient
from config import print_config

def test_session_continuity():
    """Test session continuity through OAuth proxy"""
    print_config()
    print()
    print("Testing MCP session continuity...")
    print("=" * 60)

    try:
        # Connect to MCP server
        client = MCPClient().connect()

        print("\n1. Calling tools/list...")
        tools = client.list_tools()
        print(f"Tools available: {len(tools)}")

        print("\n2. Creating a channel...")
        create_resp = client.call_tool("create_channel", {
            "name": "Session Continuity Test",
            "slots": ["invite:player1", "invite:player2"]
        })

        channel_id = create_resp["channel_id"]
        invite_code = create_resp["invites"][0]
        print(f"✅ Created channel: {channel_id}")
        print(f"   Invite code: {invite_code}")

        print("\n3. Joining the channel...")
        join_resp = client.call_tool("join_channel", {"invite_code": invite_code}, 3)
        print(f"✅ Joined channel as slot: {join_resp.get('slot_id')}")

        print("\n4. Posting a message...")
        post_resp = client.call_tool("post_message", {
            "channel_id": channel_id,
            "kind": "user",
            "body": "Test message from session test"
        }, 4)
        print(f"✅ Posted message: {post_resp.get('msg_id')}")

        print("\n5. Syncing messages...")
        sync_resp = client.call_tool("sync_messages", {"channel_id": channel_id}, 5)
        messages = sync_resp.get("messages", [])
        print(f"✅ Synced {len(messages)} messages")
        for msg in messages[-3:]:  # Show last 3 messages
            sender = msg['sender'][:8] + '...'
            body = msg.get('body', {})
            if isinstance(body, dict):
                text = body.get('text', str(body))
            else:
                text = str(body)
            print(f"   - {sender} ({msg['kind']}): {text}")

        print("\n" + "=" * 60)
        print("✅ Session continuity test completed!")
        print("If all steps succeeded, session handling is working correctly.")

    except Exception as e:
        print(f"❌ Error during session test: {e}")
        return 1

    return 0

def main():
    return test_session_continuity()

if __name__ == "__main__":
    sys.exit(main())