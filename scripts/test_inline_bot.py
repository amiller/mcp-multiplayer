#!/usr/bin/env python3
"""
Test inline bot code with a simple echo bot
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import MCPClient
from config import print_config

def test_inline_bot():
    """Test creating a channel with inline bot code"""
    print_config()
    print()
    print("Testing inline bot code...")
    print("=" * 60)

    try:
        print("\n🔐 Setting up client...")
        client = MCPClient()
        client = client.connect()
        print("✅ Connected")

        inline_code = '''
class EchoBot:
    def __init__(self, ctx, params):
        self.ctx = ctx
        self.params = params

    def on_init(self):
        self.ctx.post("bot", {"type": "ready", "message": "EchoBot is ready!"})

    def on_join(self, player_id):
        self.ctx.post("bot", {"type": "welcome", "player": player_id, "message": f"Welcome {player_id[:8]}!"})

    def on_message(self, msg):
        if msg.get("kind") == "user":
            body = msg.get("body", {})
            self.ctx.post("bot", {"type": "echo", "original": body, "message": f"I heard: {body}"})
'''

        print("\n🎮 Creating channel with inline EchoBot...")
        create_resp = client.call_tool("create_channel", {
            "name": "Echo Test",
            "slots": ["bot:echo", "invite:player1"],
            "bot_code": inline_code
        })

        channel_id = create_resp["channel_id"]
        invite = create_resp["invites"][0]
        print(f"✅ Created channel: {channel_id}")
        print(f"   Invite code: {invite}")

        print("\n👥 Joining channel...")
        join_resp = client.call_tool("join_channel", {"invite_code": invite})
        print(f"✅ Joined as slot: {join_resp.get('slot_id')}")

        print("\n📥 Checking initial messages...")
        sync_resp = client.call_tool("sync_messages", {"channel_id": channel_id})
        messages = sync_resp.get("messages", [])
        print(f"✅ Found {len(messages)} initial messages")
        for msg in messages:
            sender = msg['sender'][:12]
            body = msg.get('body', {})
            print(f"   📨 {sender} ({msg['kind']}): {body}")

        print("\n💬 Sending test message...")
        post_resp = client.call_tool("post_message", {
            "channel_id": channel_id,
            "body": "Hello EchoBot!"
        })
        print(f"✅ Message posted: {post_resp.get('msg_id')}")

        print("\n📥 Checking bot echo response...")
        sync_resp2 = client.call_tool("sync_messages", {"channel_id": channel_id})
        new_messages = sync_resp2.get("messages", [])
        recent = new_messages[len(messages):]
        print(f"✅ {len(recent)} new messages")
        for msg in recent:
            sender = msg['sender'][:12]
            body = msg.get('body', {})
            print(f"   📨 {sender} ({msg['kind']}): {body}")

        bot_echoed = any(msg.get('kind') == 'bot' and 'echo' in str(msg.get('body', {}))
                        for msg in recent)

        if bot_echoed:
            print("\n🎉 Success! EchoBot responded to the message.")
        else:
            print("\n⚠️  EchoBot didn't echo as expected")

        print("\n" + "=" * 60)
        print("✅ Inline bot test completed!")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(test_inline_bot())