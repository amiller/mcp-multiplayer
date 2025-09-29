#!/usr/bin/env python3
"""
List all available channels from the MCP server
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
        'client_name': 'Channel List Client',
        'redirect_uris': ['http://localhost/callback']
    }, verify=False)

    if reg_resp.status_code != 201:
        print(f"Registration failed: {reg_resp.status_code} {reg_resp.text}")
        return None

    client_data = reg_resp.json()

    # Get token
    creds = base64.b64encode(f'{client_data["client_id"]}:{client_data["client_secret"]}'.encode()).decode()
    token_resp = requests.post(f'{BASE_URL}/token',
        data={'grant_type': 'client_credentials', 'scope': 'mcp'},
        headers={'Authorization': f'Basic {creds}'},
        verify=False)

    if token_resp.status_code != 200:
        print(f"Token request failed: {token_resp.status_code} {token_resp.text}")
        return None

    return token_resp.json()['access_token']

def initialize_session(token):
    """Initialize MCP session"""
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
            "clientInfo": {"name": "Channel List Client", "version": "1.0.0"}
        }
    }

    init_resp = requests.post(f"{BASE_URL}/", json=init_payload, headers=headers, verify=False)
    if init_resp.status_code != 200:
        print(f"Initialize failed: {init_resp.status_code} {init_resp.text}")
        return None, None

    session_id = init_resp.headers.get('mcp-session-id')
    headers['mcp-session-id'] = session_id

    return headers, session_id

def list_channels(headers):
    """Call list_channels tool"""
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "list_channels",
            "arguments": {}
        }
    }

    resp = requests.post(f"{BASE_URL}/", json=payload, headers=headers, verify=False)
    return resp

def parse_response(resp):
    """Parse the response to extract channel data"""
    if resp.status_code != 200:
        print(f"Request failed: {resp.status_code} {resp.text}")
        return None

    print(f"Response status: {resp.status_code}")
    print(f"Raw response: {resp.text[:500]}...")

    try:
        # Try JSON first
        data = resp.json()
        print(f"JSON data keys: {data.keys()}")
        if 'result' in data and 'content' in data['result']:
            content = data['result']['content'][0]['text']
            return json.loads(content)
    except Exception as e:
        print(f"JSON parsing failed: {e}")
        # Try SSE format
        lines = resp.text.split('\n')
        for line in lines:
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'result' in data and 'content' in data['result']:
                        content = data['result']['content'][0]['text']
                        return json.loads(content)
                except Exception as e2:
                    print(f"SSE parsing failed: {e2}")
                    continue
    return None

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

def list_tools(headers):
    """List available tools first"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    resp = requests.post(f"{BASE_URL}/", json=payload, headers=headers, verify=False)
    return resp

def main():
    print("Connecting to MCP server at https://mcp.ln.soc1024.com")

    # Get OAuth token
    token = get_oauth_token()
    if not token:
        print("Failed to get OAuth token")
        return

    print(f"Got token: {token[:16]}...")

    # Initialize session
    headers, session_id = initialize_session(token)
    if not headers:
        print("Failed to initialize session")
        return

    print(f"Initialized session: {session_id}")

    # List available tools first
    print("Fetching available tools...")
    tools_resp = list_tools(headers)
    if tools_resp.status_code == 200:
        print(f"Tools response: {tools_resp.text[:500]}...")

    # List channels
    print("Fetching channel list...")
    resp = list_channels(headers)

    # Parse and display results
    channels_data = parse_response(resp)
    display_channels(channels_data)

if __name__ == "__main__":
    main()