#!/usr/bin/env python3
"""
Test bot code transparency - verify clients can retrieve and verify bot code
"""

import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import MCPClient
from config import print_config

def test_bot_transparency():
    """Test that clients can retrieve and verify bot code"""
    print_config()
    print()
    print("Testing bot code transparency...")
    print("=" * 60)

    try:
        print("\n🔐 Setting up client...")
        client = MCPClient()
        client = client.connect()
        print("✅ Connected")

        inline_code = '''
class TransparentBot:
    def __init__(self, ctx, params):
        self.ctx = ctx

    def on_init(self):
        self.ctx.post("bot", {"type": "ready", "message": "Bot initialized"})
'''

        print("\n🎮 Creating channel with inline bot...")
        create_resp = client.call_tool("create_channel", {
            "name": "Transparency Test",
            "slots": ["bot:transparent", "invite:player1"],
            "bot_code": inline_code
        })

        channel_id = create_resp["channel_id"]
        invite = create_resp["invites"][0]
        print(f"✅ Created channel: {channel_id}")

        print("\n👥 Joining channel...")
        client.call_tool("join_channel", {"invite_code": invite})
        print("✅ Joined channel")

        print("\n📥 Syncing messages to find bot:attach...")
        sync_resp = client.call_tool("sync_messages", {"channel_id": channel_id})
        messages = sync_resp.get("messages", [])

        # Find bot:attach message
        bot_attach = None
        for msg in messages:
            if msg.get("kind") == "system" and msg.get("body", {}).get("type") == "bot:attach":
                bot_attach = msg["body"]
                break

        if not bot_attach:
            print("❌ No bot:attach message found")
            return 1

        bot_id = bot_attach["bot_id"]
        posted_code_hash = bot_attach["code_hash"]
        posted_manifest_hash = bot_attach["manifest_hash"]

        print(f"✅ Found bot:attach message")
        print(f"   Bot ID: {bot_id}")
        print(f"   Code hash: {posted_code_hash}")
        print(f"   Manifest hash: {posted_manifest_hash}")

        print("\n🔍 Retrieving bot code for verification...")
        bot_code_resp = client.call_tool("get_bot_code", {
            "channel_id": channel_id,
            "bot_id": bot_id
        })

        retrieved_code = bot_code_resp["inline_code"]
        retrieved_code_hash = bot_code_resp["code_hash"]
        retrieved_manifest_hash = bot_code_resp["manifest_hash"]

        print(f"✅ Retrieved bot code")
        print(f"   Code hash: {retrieved_code_hash}")
        print(f"   Manifest hash: {retrieved_manifest_hash}")

        # Verify hashes match
        print("\n🔐 Verifying code transparency...")
        if posted_code_hash == retrieved_code_hash:
            print("✅ Code hash matches!")
        else:
            print(f"❌ Code hash mismatch!")
            print(f"   Posted: {posted_code_hash}")
            print(f"   Retrieved: {retrieved_code_hash}")
            return 1

        if posted_manifest_hash == retrieved_manifest_hash:
            print("✅ Manifest hash matches!")
        else:
            print(f"❌ Manifest hash mismatch!")
            return 1

        # Verify we can recompute the hash ourselves
        print("\n🔬 Verifying hash computation...")
        our_hash = "sha256:" + hashlib.sha256(retrieved_code.encode()).hexdigest()
        if our_hash == retrieved_code_hash:
            print("✅ Successfully recomputed code hash - bot is transparent!")
        else:
            print(f"❌ Hash recomputation failed!")
            print(f"   Our hash: {our_hash}")
            print(f"   Bot hash: {retrieved_code_hash}")
            return 1

        print("\n📝 Retrieved bot code:")
        print(retrieved_code)

        print("\n" + "=" * 60)
        print("🎉 Bot transparency verified!")
        print("   - Bot code hash posted to channel (common knowledge)")
        print("   - Bot code retrieved and verified")
        print("   - Hash independently recomputed")
        print("✅ Trust established through transparency!")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(test_bot_transparency())