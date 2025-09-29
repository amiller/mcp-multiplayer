#!/usr/bin/env python3
"""
Channel creation script that follows Claude's exact MCP pattern
"""

import requests
import json
import re
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

disable_warnings(InsecureRequestWarning)

BASE_URL = "https://mcp.ln.soc1024.com"

def main():
    print("Creating channel via proper MCP session flow...")

    # Step 1: Initialize MCP session (like Claude does)
    init_payload = {
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "channel-creator",
                "version": "1.0.0"
            }
        },
        "jsonrpc": "2.0",
        "id": 0
    }

    init_resp = requests.post(f"{BASE_URL}/",
        json=init_payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        },
        verify=False
    )

    if init_resp.status_code != 200:
        print(f"Initialize failed: {init_resp.status_code} {init_resp.text}")
        return

    # Extract session ID from response
    session_id = init_resp.headers.get('mcp-session-id')
    print(f"Got session ID: {session_id}")

    if not session_id:
        print("No session ID in response!")
        return

    # Step 2: Send initialized notification (like Claude does)
    init_notify = {
        "method": "notifications/initialized",
        "jsonrpc": "2.0"
    }

    notify_resp = requests.post(f"{BASE_URL}/",
        json=init_notify,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Session-Id": session_id,
            "Mcp-Protocol-Version": "2025-06-18"
        },
        verify=False
    )

    print(f"Initialized notification: {notify_resp.status_code}")

    # Step 3: Create channel using proper session
    create_payload = {
        "method": "tools/call",
        "params": {
            "name": "create_channel",
            "arguments": {
                "name": "Test Channel",
                "slots": ["invite:player1", "invite:player2"]
            }
        },
        "jsonrpc": "2.0",
        "id": 1
    }

    create_resp = requests.post(f"{BASE_URL}/",
        json=create_payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Session-Id": session_id,
            "Mcp-Protocol-Version": "2025-06-18"
        },
        verify=False
    )

    print(f"Create channel response: {create_resp.status_code}")

    if create_resp.status_code == 200:
        # Parse SSE response
        lines = create_resp.text.split('\n')
        for line in lines:
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'result' in data:
                        content = data['result']['content'][0]['text']
                        channel_data = json.loads(content)
                        print(f"\n✅ SUCCESS! Created channel:")
                        print(f"   Channel ID: {channel_data['channel_id']}")
                        print(f"   Invite codes:")
                        for i, invite in enumerate(channel_data['invites']):
                            print(f"     Player {i+1}: {invite}")
                        print("\nYou can now use these invite codes!")
                        return
                    elif 'error' in data:
                        print(f"Error: {data['error']}")
                        return
                except Exception as e:
                    print(f"Parse error: {e}")
                    continue

    print(f"Failed to create channel: {create_resp.text}")

if __name__ == "__main__":
    main()