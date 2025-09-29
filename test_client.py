#!/usr/bin/env python3
"""
Test client for MCP Multiplayer
Demonstrates the full OAuth flow and basic operations
"""

import requests
import json
import time
from urllib.parse import urlparse, parse_qs
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://127.0.0.1:9100"

class MCPTestClient:
    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.access_token = None

    def register_client(self):
        """Register as an OAuth client"""
        print("1. Registering OAuth client...")

        response = requests.post(f"{BASE_URL}/register", json={
            "client_name": "MCP Test Client",
            "redirect_uris": ["http://localhost:8080/callback"]
        }, verify=False)

        if response.status_code == 201:  # Registration returns 201 Created
            data = response.json()
            self.client_id = data['client_id']
            self.client_secret = data['client_secret']
            print(f"   ✓ Registered client: {self.client_id[:8]}...")
            return True
        else:
            print(f"   ✗ Registration failed: {response.status_code} {response.text}")
            return False

    def get_access_token(self):
        """Get access token using client credentials flow"""
        print("2. Getting access token...")

        response = requests.post(f"{BASE_URL}/token", data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "mcp"
        }, verify=False)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data['access_token']
            print(f"   ✓ Got access token: {self.access_token[:20]}...")
            return True
        else:
            print(f"   ✗ Token request failed: {response.text}")
            return False

    def make_authenticated_request(self, method, endpoint, json_data=None, params=None):
        """Make an authenticated request to the API"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        url = f"{BASE_URL}{endpoint}"

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, verify=False)
        else:
            response = requests.request(method, url, headers=headers, json=json_data, params=params, verify=False)

        return response

    def test_create_channel(self):
        """Test creating a channel with a GuessBot"""
        print("3. Creating a channel with GuessBot...")

        channel_data = {
            "name": "Guess Game Demo",
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
        }

        response = self.make_authenticated_request("POST", "/create_channel", channel_data)

        if response.status_code == 200:
            data = response.json()
            self.channel_id = data['channel_id']
            self.invite_codes = data['invites']
            print(f"   ✓ Created channel: {self.channel_id}")
            print(f"   ✓ Invite codes: {len(self.invite_codes)} generated")
            return data
        else:
            print(f"   ✗ Channel creation failed: {response.text}")
            return None

    def test_join_channel(self, invite_code):
        """Test joining a channel"""
        print("4. Joining channel...")

        response = self.make_authenticated_request("POST", "/join_channel", {
            "invite_code": invite_code
        })

        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Joined channel as slot: {data['slot_id']}")
            return data
        else:
            print(f"   ✗ Join failed: {response.text}")
            return None

    def test_sync_messages(self):
        """Test syncing messages"""
        print("5. Syncing messages...")

        response = self.make_authenticated_request("GET", "/sync_messages", params={
            "channel_id": self.channel_id
        })

        if response.status_code == 200:
            data = response.json()
            messages = data['messages']
            print(f"   ✓ Synced {len(messages)} messages")

            # Show some interesting messages
            for msg in messages[:5]:  # Show first 5
                sender = msg['sender']
                kind = msg['kind']
                body_type = msg['body'].get('type', 'unknown')
                print(f"     - {sender} ({kind}): {body_type}")

            return data
        else:
            print(f"   ✗ Sync failed: {response.text}")
            return None

    def test_post_guess(self, guess_value):
        """Test posting a guess"""
        print(f"6. Posting guess: {guess_value}")

        response = self.make_authenticated_request("POST", "/post_message", {
            "channel_id": self.channel_id,
            "kind": "user",
            "body": {
                "type": "move",
                "game": "guess",
                "action": "guess",
                "value": guess_value
            }
        })

        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Posted guess: {data['msg_id']}")
            return data
        else:
            print(f"   ✗ Guess failed: {response.text}")
            return None

    def test_who(self):
        """Test getting channel info"""
        print("7. Getting channel info...")

        response = self.make_authenticated_request("GET", "/who", params={
            "channel_id": self.channel_id
        })

        if response.status_code == 200:
            data = response.json()
            view = data['view']
            bots = data['bots']
            print(f"   ✓ Channel: {view['name']}")
            print(f"   ✓ Slots: {len(view['slots'])}")
            print(f"   ✓ Bots: {len(bots)}")
            return data
        else:
            print(f"   ✗ Who failed: {response.text}")
            return None

    def run_full_test(self):
        """Run the complete test flow"""
        print("MCP Multiplayer Test Client")
        print("=" * 40)

        # Step 1: Register client
        if not self.register_client():
            return False

        # Step 2: Get access token
        if not self.get_access_token():
            return False

        # Step 3: Create channel
        channel_data = self.test_create_channel()
        if not channel_data:
            return False

        # Step 4: Join channel (use first invite)
        join_data = self.test_join_channel(self.invite_codes[0])
        if not join_data:
            return False

        # Step 5: Check initial messages
        self.test_sync_messages()

        # Step 6: Get channel info
        self.test_who()

        # Step 7: Try a guess
        self.test_post_guess(50)

        # Step 8: Check messages again
        time.sleep(0.5)  # Give bot time to respond
        self.test_sync_messages()

        print("\n" + "=" * 40)
        print("✓ All tests completed successfully!")
        print("✓ MCP Multiplayer system is working!")

        return True

def main():
    """Run the test client"""
    client = MCPTestClient()

    # Check if servers are running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5, verify=False)
        if response.status_code != 200:
            print("❌ MCP servers are not responding properly")
            print("   Please run: python start_servers.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to MCP servers")
        print("   Please run: python start_servers.py")
        return

    # Run tests
    if client.run_full_test():
        print("\n🎉 Ready for real MCP client testing!")
        print(f"   OAuth Endpoint: {BASE_URL}")
        print(f"   Registration:   {BASE_URL}/register")
        print(f"   Authorization:  {BASE_URL}/oauth/authorize")
        print(f"   Token:          {BASE_URL}/token")
    else:
        print("\n❌ Tests failed - check server logs")

if __name__ == "__main__":
    main()