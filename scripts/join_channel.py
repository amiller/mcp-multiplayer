#!/usr/bin/env python3
"""
Join a channel using invite code
"""

import sys
import os

# Add the scripts directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import MCPClient
from config import print_config

def main():
    if len(sys.argv) < 2:
        print("Usage: python join_channel.py <invite_code>")
        print("Example: python join_channel.py inv_abc123...")
        return 1

    invite_code = sys.argv[1]

    print_config()
    print()
    print(f"Joining channel with invite code: {invite_code}")

    try:
        # Connect to MCP server
        client = MCPClient().connect()

        # Join the channel
        print("Joining channel...")
        join_data = client.call_tool("join_channel", {
            "invite_code": invite_code
        })

        print(f"\n✅ Successfully joined!")
        print(f"Channel: {join_data['view']['name']}")
        print(f"Your slot: {join_data['slot_id']}")
        print(f"Channel ID: {join_data['channel_id']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())