#!/usr/bin/env python3
"""
Channel creation script that follows Claude's exact MCP pattern
"""

import sys
import os

# Add the scripts directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import MCPClient
from config import print_config

def main():
    print_config()
    print()

    try:
        # Connect to MCP server
        client = MCPClient().connect()

        # Create channel with guessing game bot
        print("Creating channel with guessing game bot...")
        channel_data = client.call_tool("create_channel", {
            "name": "Guessing Game",
            "slots": ["bot:guess-referee", "invite:player1", "invite:player2"],
            "bots": [{
                "name": "GuessBot",
                "version": "1.0",
                "code_ref": "builtin://GuessBot",
                "manifest": {
                    "summary": "Turn-based number guessing referee",
                    "hooks": ["on_init", "on_join", "on_message"],
                    "emits": ["prompt", "state", "turn", "judge"],
                    "params": {"mode": "number", "range": [1, 100]}
                }
            }]
        })

        print("\nSUCCESS! Created channel:")
        print(f"   Channel ID: {channel_data['channel_id']}")
        print(f"   Invite codes:")
        for i, invite in enumerate(channel_data['invites']):
            print(f"     Player {i+1}: {invite}")
        print("\nYou can now use these invite codes!")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())