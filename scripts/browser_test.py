#!/usr/bin/env python3
"""
Test script to create Browser Test Channel via HTTPS
"""

import json
import requests
import base64
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

disable_warnings(InsecureRequestWarning)

BASE_URL = "https://mcp.ln.soc1024.com"

def get_oauth_token():
    """Get OAuth token"""
    print("🔐 Getting OAuth token...")

    # Register client
    reg_resp = requests.post(f'{BASE_URL}/register', json={
        'client_name': 'Browser Test Channel Creator',
        'redirect_uris': ['http://localhost/callback']
    }, verify=False)

    if reg_resp.status_code != 201:
        print(f"❌ Registration failed: {reg_resp.status_code} {reg_resp.text}")
        return None

    client_data = reg_resp.json()

    # Get token using client credentials
    creds = base64.b64encode(f'{client_data["client_id"]}:{client_data["client_secret"]}'.encode()).decode()
    token_resp = requests.post(f'{BASE_URL}/token',
        data={'grant_type': 'client_credentials', 'scope': 'mcp'},
        headers={'Authorization': f'Basic {creds}'},
        verify=False)

    if token_resp.status_code != 200:
        print(f"❌ Token request failed: {token_resp.status_code} {token_resp.text}")
        return None

    token_data = token_resp.json()
    print(f"✅ Got access token: {token_data['access_token'][:16]}...")
    return token_data['access_token']

def main():
    token = get_oauth_token()
    if not token:
        return

    # Prepare headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    # Initialize MCP session
    print("🚀 Initializing MCP session...")
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "experimental": {},
                "prompts": {"listChanged": True},
                "resources": {"subscribe": False, "listChanged": True},
                "tools": {"listChanged": True}
            },
            "clientInfo": {
                "name": "Browser Test Channel Creator",
                "version": "1.0.0"
            }
        }
    }

    init_resp = requests.post(f"{BASE_URL}/", json=init_payload, headers=headers, verify=False)
    if init_resp.status_code != 200:
        print(f"❌ Initialize failed: {init_resp.status_code}")
        print(f"Response: {init_resp.text}")
        return

    session_id = init_resp.headers.get('mcp-session-id')
    print(f"✅ Initialized session: {session_id}")

    # Add session to headers
    headers['mcp-session-id'] = session_id

    # List available tools first
    print("🔧 Listing available tools...")
    list_tools_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }

    tools_resp = requests.post(f"{BASE_URL}/", json=list_tools_payload, headers=headers, verify=False)
    if tools_resp.status_code == 200:
        try:
            # Handle SSE response
            if tools_resp.text.startswith('event: message\ndata: '):
                data_line = tools_resp.text.split('\ndata: ')[1].split('\n')[0]
                tools_data = json.loads(data_line)
            else:
                tools_data = tools_resp.json()

            if 'result' in tools_data:
                tools = tools_data['result']['tools']
                print(f"✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']}: {tool['description']}")
        except Exception as e:
            print(f"⚠️  Could not parse tools list: {e}")

    # Create the Browser Test Channel
    print("🏗️  Creating Browser Test Channel...")
    create_payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "create_channel",
            "arguments": {
                "name": "Browser Test Channel",
                "slots": ["invite:player1", "invite:player2", "invite:player3"]
            }
        }
    }

    create_resp = requests.post(f"{BASE_URL}/", json=create_payload, headers=headers, verify=False)
    print(f"Create channel response: {create_resp.status_code}")

    if create_resp.status_code == 200:
        try:
            # Handle SSE response format
            response_text = create_resp.text
            print(f"Raw response: {response_text[:300]}...")

            if response_text.startswith('event: message\ndata: '):
                # Parse SSE format
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        data = json.loads(line[6:])
                        if 'result' in data:
                            content = data['result']['content'][0]['text']
                            channel_data = json.loads(content)

                            print("\n" + "="*60)
                            print("🎉 BROWSER TEST CHANNEL CREATED SUCCESSFULLY!")
                            print("="*60)
                            print(f"📋 Channel ID: {channel_data['channel_id']}")
                            print(f"📛 Channel Name: Browser Test Channel")
                            print(f"🎫 Invite Codes (for Claude browser):")
                            for i, invite in enumerate(channel_data['invites']):
                                print(f"   Player {i+1}: {invite}")
                            print("="*60)
                            print("\n✅ Test completed! The invite codes above can be used")
                            print("   by users in Claude browser to join the channel.")
                            return
                        elif 'error' in data:
                            print(f"❌ MCP Error: {data['error']}")
                            return
            else:
                # Try regular JSON
                data = create_resp.json()
                if 'result' in data:
                    content = data['result']['content'][0]['text']
                    channel_data = json.loads(content)
                    print(f"✅ Channel created: {channel_data['channel_id']}")
                    print(f"🎫 Invite codes: {channel_data['invites']}")
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            print(f"Raw response: {create_resp.text}")
    else:
        print(f"❌ Create channel failed: {create_resp.status_code}")
        print(f"Response: {create_resp.text}")

if __name__ == "__main__":
    main()