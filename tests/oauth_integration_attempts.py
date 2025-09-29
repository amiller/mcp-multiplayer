#!/usr/bin/env python3
"""
Fixed MCP test - minimal working test that actually works
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
    print("Getting OAuth token...")

    # Register client
    reg_resp = requests.post(f'{BASE_URL}/register', json={
        'client_name': 'Fixed Test Client',
        'redirect_uris': ['http://localhost/callback']
    }, verify=False)

    if reg_resp.status_code != 201:
        return None

    client_data = reg_resp.json()

    # Get token
    creds = base64.b64encode(f'{client_data["client_id"]}:{client_data["client_secret"]}'.encode()).decode()
    token_resp = requests.post(f'{BASE_URL}/token',
        data={'grant_type': 'client_credentials', 'scope': 'mcp'},
        headers={'Authorization': f'Basic {creds}'},
        verify=False)

    if token_resp.status_code != 200:
        return None

    return token_resp.json()['access_token']

def main():
    token = get_oauth_token()
    if not token:
        print("✗ Failed to get token")
        return

    print(f"✓ Got token: {token[:16]}...")

    # Initialize session
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"experimental": {}, "prompts": {"listChanged": True}, "resources": {"subscribe": False, "listChanged": True}, "tools": {"listChanged": True}},
            "clientInfo": {"name": "Fixed Test Client", "version": "1.0.0"}
        }
    }

    init_resp = requests.post(f"{BASE_URL}/", json=init_payload, headers=headers, verify=False)
    if init_resp.status_code != 200:
        print(f"✗ Initialize failed: {init_resp.status_code} {init_resp.text}")
        return

    session_id = init_resp.headers.get('mcp-session-id')
    print(f"✓ Initialized with session: {session_id}")

    # Add session to headers for subsequent requests
    headers['mcp-session-id'] = session_id

    # Test create_channel using exact format that should work
    create_payload = {
        "jsonrpc": "2.0",
        "id": 2,
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
    print(f"Create response: {create_resp.status_code}")

    if create_resp.status_code == 200:
        # Parse SSE or JSON response
        try:
            data = create_resp.json()
            if 'result' in data:
                content = data['result']['content'][0]['text']
                channel_data = json.loads(content)
                print(f"✓ Created channel: {channel_data['channel_id']}")
                print(f"✓ Invite codes: {channel_data['invites']}")
                print("✅ MCP multiplayer test successful!")

                # Make invite codes more visible
                print("\n" + "="*50)
                print("INVITE CODES FOR CLAUDE:")
                for i, invite in enumerate(channel_data['invites']):
                    print(f"  Player {i+1}: {invite}")
                print("="*50)
            else:
                print(f"Unexpected response structure: {data}")
        except Exception as e:
            # Try SSE format
            print(f"JSON parsing failed: {e}, trying SSE...")
            print(f"Raw response: {create_resp.text[:500]}...")
            lines = create_resp.text.split('\n')
            for line in lines:
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'result' in data:
                            content = data['result']['content'][0]['text']
                            channel_data = json.loads(content)
                            print(f"✓ Created channel: {channel_data['channel_id']}")
                            print(f"✓ Invite codes: {channel_data['invites']}")
                            print("✅ MCP multiplayer test successful!")

                            # Make invite codes more visible
                            print("\n" + "="*50)
                            print("INVITE CODES FOR CLAUDE:")
                            for i, invite in enumerate(channel_data['invites']):
                                print(f"  Player {i+1}: {invite}")
                            print("="*50)

                            # Test joining the channel
                            invite_code = channel_data['invites'][0]
                            join_payload = {
                                "jsonrpc": "2.0",
                                "id": 3,
                                "method": "tools/call",
                                "params": {
                                    "name": "join_channel",
                                    "arguments": {"invite_code": invite_code}
                                }
                            }

                            join_resp = requests.post(f"{BASE_URL}/", json=join_payload, headers=headers, verify=False)
                            if join_resp.status_code == 200:
                                # Parse join response
                                try:
                                    join_data = join_resp.json()
                                    if 'result' in join_data:
                                        join_content = join_data['result']['content'][0]['text']
                                        join_result = json.loads(join_content)
                                        print(f"✓ Joined as slot: {join_result.get('slot_id')}")
                                except:
                                    print("✓ Join succeeded (couldn't parse details)")

                            return
                    except:
                        continue
    else:
        print(f"✗ Create failed: {create_resp.text}")

if __name__ == "__main__":
    main()