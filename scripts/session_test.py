#!/usr/bin/env python3
"""
Test MCP session handling through OAuth proxy at mcp.ln.soc1024.com
This reproduces the session issue that Claude experiences.
"""

import json
import requests
import base64
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

disable_warnings(InsecureRequestWarning)

BASE_URL = "https://127.0.0.1:9100"

def get_oauth_token():
    """Get OAuth token for testing"""
    print("Getting OAuth token...")

    # Register client
    reg_resp = requests.post(f'{BASE_URL}/register', json={
        'client_name': 'Session Test Client',
        'redirect_uris': ['http://localhost/callback']
    }, verify=False)

    if reg_resp.status_code != 201:
        print(f"Registration failed: {reg_resp.status_code} {reg_resp.text}")
        return None

    client_data = reg_resp.json()
    print(f"Registered client: {client_data['client_id'][:8]}...")

    # Get token
    creds = base64.b64encode(f'{client_data["client_id"]}:{client_data["client_secret"]}'.encode()).decode()
    token_resp = requests.post(f'{BASE_URL}/token',
        data={'grant_type': 'client_credentials', 'scope': 'mcp'},
        headers={'Authorization': f'Basic {creds}'},
        verify=False)

    if token_resp.status_code != 200:
        print(f"Token request failed: {token_resp.status_code} {token_resp.text}")
        return None

    token = token_resp.json()['access_token']
    print(f"Got token: {token[:20]}...")
    return token

def make_mcp_request(token, method, params=None):
    """Make an MCP request through the OAuth proxy"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    response = requests.post(f"{BASE_URL}/", json=payload, headers=headers, verify=False)
    print(f"MCP Request: {method} -> {response.status_code}")

    if response.status_code == 200:
        # Handle SSE response
        try:
            return response.json()
        except:
            # Parse SSE format
            lines = response.text.split('\n')
            for line in lines:
                if line.startswith('data: '):
                    try:
                        return json.loads(line[6:])
                    except:
                        continue
            return {"error": "Could not parse response"}
    else:
        return {"error": f"{response.status_code} {response.text}"}

def test_session_continuity():
    """Test session continuity through OAuth proxy"""
    print("Testing MCP session continuity via mcp.ln.soc1024.com")
    print("=" * 60)

    # Get OAuth token
    token = get_oauth_token()
    if not token:
        return

    print("\n1. Calling tools/list...")
    list_resp = make_mcp_request(token, "tools/list")
    print(f"Tools available: {len(list_resp.get('result', {}).get('tools', []))}")

    print("\n2. Creating a channel...")
    create_resp = make_mcp_request(token, "tools/call", {
        "name": "create_channel",
        "arguments": {
            "name": "Session Continuity Test",
            "slots": ["invite:player1", "invite:player2"]
        }
    })

    if "error" in create_resp:
        print(f"❌ Create failed: {create_resp}")
        return

    try:
        content = create_resp["result"]["content"][0]["text"]
        channel_data = json.loads(content)
        channel_id = channel_data["channel_id"]
        invite_code = channel_data["invites"][0]
        print(f"✅ Created channel: {channel_id}")
        print(f"   Invite code: {invite_code}")
    except Exception as e:
        print(f"❌ Failed to parse create response: {e}")
        print(f"   Response: {create_resp}")
        return

    print("\n3. Joining the channel...")
    join_resp = make_mcp_request(token, "tools/call", {
        "name": "join_channel",
        "arguments": {"invite_code": invite_code}
    })

    if "error" in join_resp:
        print(f"❌ Join failed: {join_resp}")
        print("   This indicates session continuity issues!")
        return

    try:
        content = join_resp["result"]["content"][0]["text"]
        join_data = json.loads(content)
        print(f"✅ Joined channel as slot: {join_data.get('slot_id')}")
    except Exception as e:
        print(f"❌ Failed to parse join response: {e}")
        print(f"   Response: {join_resp}")
        return

    print("\n4. Posting a message...")
    post_resp = make_mcp_request(token, "tools/call", {
        "name": "post_message",
        "arguments": {
            "channel_id": channel_id,
            "kind": "user",
            "body": "Test message from session test"
        }
    })

    if "error" in post_resp:
        print(f"❌ Post failed: {post_resp}")
    else:
        try:
            content = post_resp["result"]["content"][0]["text"]
            post_data = json.loads(content)
            print(f"✅ Posted message: {post_data.get('msg_id')}")
        except Exception as e:
            print(f"❌ Failed to parse post response: {e}")

    print("\n5. Syncing messages...")
    sync_resp = make_mcp_request(token, "tools/call", {
        "name": "sync_messages",
        "arguments": {"channel_id": channel_id}
    })

    if "error" in sync_resp:
        print(f"❌ Sync failed: {sync_resp}")
    else:
        try:
            content = sync_resp["result"]["content"][0]["text"]
            sync_data = json.loads(content)
            messages = sync_data.get("messages", [])
            print(f"✅ Synced {len(messages)} messages")
            for msg in messages[-3:]:  # Show last 3 messages
                print(f"   - {msg['sender'][:8]}... ({msg['kind']}): {msg.get('body', {}).get('text', str(msg.get('body')))}")
        except Exception as e:
            print(f"❌ Failed to parse sync response: {e}")

    print("\n" + "=" * 60)
    print("✅ Session continuity test completed!")
    print("If all steps succeeded, session handling is working correctly.")

if __name__ == "__main__":
    test_session_continuity()