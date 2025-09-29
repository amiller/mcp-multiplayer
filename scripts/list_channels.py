#!/usr/bin/env python3
"""
List all available channels from the MCP server
"""

import json
import sys
import os

# Add the scripts directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import MCPClient
from config import print_config

def display_channels(channels_data):
    """Display channel information in a formatted way"""
    if not channels_data:
        print("No channel data received")
        return

    channels = channels_data.get('channels', [])
    total = channels_data.get('total_channels', 0)

    print(f"\n{'='*60}")
    print(f"AVAILABLE CHANNELS ({total} total)")
    print(f"{'='*60}")

    if not channels:
        print("No channels currently available")
        return

    for i, channel in enumerate(channels, 1):
        print(f"\n{i}. {channel['name']}")
        print(f"   Channel ID: {channel['channel_id']}")
        print(f"   Total Slots: {len(channel['slots'])}")
        print(f"   Message Count: {channel['message_count']}")

        # Display slot details
        print(f"   Slots:")
        for j, slot in enumerate(channel['slots']):
            slot_type = slot.get('slot_type', 'unknown')
            slot_id = slot.get('slot_id', 'N/A')
            occupied = slot.get('occupied', False)
            invite_code = slot.get('invite_code', 'N/A')

            status = "OCCUPIED" if occupied else "AVAILABLE"
            print(f"     {j+1}. {slot_type} ({slot_id}) - {status}")

            if slot_type.startswith('invite:') and not occupied and invite_code != 'N/A':
                print(f"        Invite Code: {invite_code}")

        # Display bot information
        if channel.get('bots'):
            print(f"   Bots: {', '.join(channel['bots'])}")
        else:
            print(f"   Bots: None")

    print(f"\n{'='*60}")

def main():
    print_config()
    print()

    try:
        # Connect to MCP server
        client = MCPClient().connect()

        # List channels
        print("Fetching channel list...")
        channels_data = client.call_tool("list_channels")

        # Display results
        display_channels(channels_data)

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())