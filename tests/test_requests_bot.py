#!/usr/bin/env python3
"""Test that requests module works in sandboxed bots"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from mcp_client import MCPClient
from config import print_config

def test_requests_bot():
    print_config()
    print("\nTesting requests module in bot sandbox...")
    print("=" * 60)

    bot_code = """
import requests
import json

class RequestsBot:
    def __init__(self, ctx, params):
        self.ctx = ctx

    def on_init(self):
        try:
            # Test simple API request
            resp = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=BTC")
            data = resp.json()
            btc_usd = data["data"]["rates"]["USD"]

            self.ctx.post("bot", {
                "type": "ready",
                "message": f"Requests working! BTC price: ${btc_usd}"
            })
        except Exception as e:
            self.ctx.post("bot", {
                "type": "error",
                "message": f"Failed: {str(e)}"
            })

    def on_message(self, msg):
        if msg.get("kind") == "user":
            self.ctx.post("bot", {"echo": msg.get("body")})
"""

    try:
        client = MCPClient().connect()
        print("✅ Connected")

        print("\n🔍 Creating channel with requests bot...")
        create_resp = client.call_tool("create_channel", {
            "name": "Requests Test",
            "slots": ["bot:req", "invite:admin"],
            "bot_code": bot_code
        })

        if "channel_id" in str(create_resp):
            channel_id = create_resp["channel_id"]
            print(f"✅ Channel created: {channel_id}")

            # Join and check messages
            invite = create_resp["invites"][0]
            client.call_tool("join_channel", {"invite_code": invite})

            sync_resp = client.call_tool("sync_messages", {"channel_id": channel_id})

            for msg in sync_resp["messages"]:
                if msg.get("kind") == "bot":
                    body = msg.get("body", {})
                    print(f"\n📨 Bot response:")
                    print(f"   Type: {body.get('type')}")
                    print(f"   Message: {body.get('message')}")

                    if "BTC price" in body.get("message", ""):
                        print("\n✅ Requests module works in sandbox!")
                        return 0
                    elif "Failed" in body.get("message", ""):
                        print(f"\n❌ Requests failed: {body.get('message')}")
                        return 1
        else:
            print(f"❌ Failed to create channel: {create_resp}")
            return 1

        print("\n❌ No bot response received")
        return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_requests_bot())
