#!/usr/bin/env python3
"""
Self-contained OAuth + MCP flow test
Tests full OAuth authentication -> MCP session -> channel operations
Requires running oauth_proxy and multiplayer_server
"""

import pytest
import requests
import json
import base64
import subprocess
import time
import urllib3
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)

class OAuthMCPClient:
    def __init__(self, base_url="https://127.0.0.1:9100"):
        self.base_url = base_url
        self.token = None
        self.session_id = None

    def register_and_get_token(self):
        """Complete OAuth flow to get access token"""
        # Register client
        reg_resp = requests.post(f'{self.base_url}/register',
            json={'client_name': 'OAuth MCP Test', 'redirect_uris': ['http://localhost/callback']},
            verify=False)

        if reg_resp.status_code != 201:
            raise Exception(f"Registration failed: {reg_resp.status_code} {reg_resp.text}")

        client_data = reg_resp.json()

        # Get token
        creds = base64.b64encode(f'{client_data["client_id"]}:{client_data["client_secret"]}'.encode()).decode()
        token_resp = requests.post(f'{self.base_url}/token',
            data={'grant_type': 'client_credentials', 'scope': 'mcp'},
            headers={'Authorization': f'Basic {creds}'},
            verify=False)

        if token_resp.status_code != 200:
            raise Exception(f"Token request failed: {token_resp.status_code} {token_resp.text}")

        self.token = token_resp.json()['access_token']
        return self.token

    def initialize_mcp_session(self):
        """Initialize MCP session and capture session ID"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"experimental": {}, "tools": {"listChanged": True}},
                "clientInfo": {"name": "OAuth MCP Test", "version": "1.0.0"}
            }
        }

        init_resp = requests.post(f"{self.base_url}/", json=init_payload, headers=headers, verify=False)
        if init_resp.status_code != 200:
            raise Exception(f"MCP initialize failed: {init_resp.status_code} {init_resp.text}")

        self.session_id = init_resp.headers.get('mcp-session-id')
        if not self.session_id:
            raise Exception("No session ID returned from initialize")

        # Send initialized notification
        headers['mcp-session-id'] = self.session_id
        notify_payload = {"method": "notifications/initialized", "jsonrpc": "2.0"}

        notify_resp = requests.post(f"{self.base_url}/", json=notify_payload, headers=headers, verify=False)
        if notify_resp.status_code not in [200, 202]:
            raise Exception(f"MCP initialized notification failed: {notify_resp.status_code}")

        return self.session_id

    def call_tool(self, tool_name, arguments, request_id=1):
        """Call MCP tool with proper session headers"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": self.session_id
        }

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }

        resp = requests.post(f"{self.base_url}/", json=payload, headers=headers, verify=False)
        if resp.status_code != 200:
            raise Exception(f"Tool call failed: {resp.status_code} {resp.text}")

        # Parse response (could be JSON or SSE)
        try:
            return resp.json()
        except:
            # Parse SSE format
            lines = resp.text.split('\n')
            for line in lines:
                if line.startswith('data: '):
                    try:
                        return json.loads(line[6:])
                    except:
                        continue
            raise Exception(f"Could not parse response: {resp.text}")

@pytest.fixture(scope="session")
def servers_running():
    """Ensure servers are running for tests"""
    # Check if servers are responding
    try:
        resp = requests.get("https://127.0.0.1:9100/.well-known/oauth-authorization-server", verify=False, timeout=2)
        if resp.status_code != 200:
            pytest.skip("OAuth proxy not running on port 9100")
    except:
        pytest.skip("OAuth proxy not running on port 9100")

    try:
        resp = requests.post("http://127.0.0.1:9201/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            timeout=2)
        if resp.status_code not in [200, 400]:  # 400 is expected without proper session
            pytest.skip("MCP server not running on port 9201")
    except:
        pytest.skip("MCP server not running on port 9201")

def test_oauth_flow_works(servers_running):
    """Test OAuth registration and token generation"""
    client = OAuthMCPClient()
    token = client.register_and_get_token()

    assert token is not None
    assert len(token) > 10
    assert isinstance(token, str)

def test_mcp_session_initialization(servers_running):
    """Test MCP session initialization with OAuth token"""
    client = OAuthMCPClient()
    client.register_and_get_token()
    session_id = client.initialize_mcp_session()

    assert session_id is not None
    assert len(session_id) > 10
    assert isinstance(session_id, str)

def test_full_channel_creation_flow(servers_running):
    """Test complete OAuth -> MCP -> channel creation flow"""
    client = OAuthMCPClient()

    # Step 1: OAuth authentication
    token = client.register_and_get_token()
    assert token is not None

    # Step 2: MCP session initialization
    session_id = client.initialize_mcp_session()
    assert session_id is not None

    # Step 3: Create channel
    create_resp = client.call_tool("create_channel", {
        "name": "OAuth Flow Test Channel",
        "slots": ["invite:alice", "invite:bob"]
    })

    assert "result" in create_resp
    content = create_resp["result"]["content"][0]["text"]
    channel_data = json.loads(content)

    assert "channel_id" in channel_data
    assert "invites" in channel_data
    assert len(channel_data["invites"]) == 2

    channel_id = channel_data["channel_id"]
    invite_code = channel_data["invites"][0]

    # Step 4: Join channel
    join_resp = client.call_tool("join_channel", {"invite_code": invite_code}, 2)

    assert "result" in join_resp
    join_content = join_resp["result"]["content"][0]["text"]
    join_data = json.loads(join_content)

    assert join_data["channel_id"] == channel_id
    assert "slot_id" in join_data

    # Step 5: Post message
    post_resp = client.call_tool("post_message", {
        "channel_id": channel_id,
        "kind": "user",
        "body": "Test message from OAuth flow"
    }, 3)

    assert "result" in post_resp
    post_content = post_resp["result"]["content"][0]["text"]
    post_data = json.loads(post_content)

    assert "msg_id" in post_data

    # Step 6: Sync messages
    sync_resp = client.call_tool("sync_messages", {"channel_id": channel_id}, 4)

    assert "result" in sync_resp
    sync_content = sync_resp["result"]["content"][0]["text"]
    sync_data = json.loads(sync_content)

    messages = sync_data["messages"]
    assert len(messages) >= 1

    # Find our test message
    user_messages = [m for m in messages if m["kind"] == "user"]
    assert len(user_messages) >= 1

    test_msg = next((m for m in user_messages if m["body"] == "Test message from OAuth flow"), None)
    assert test_msg is not None

def test_two_clients_multiplayer_game(servers_running):
    """Test two OAuth clients playing together"""
    alice = OAuthMCPClient()
    bob = OAuthMCPClient()

    # Both clients authenticate
    alice.register_and_get_token()
    alice.initialize_mcp_session()

    bob.register_and_get_token()
    bob.initialize_mcp_session()

    # Alice creates channel
    create_resp = alice.call_tool("create_channel", {
        "name": "Two Player Test",
        "slots": ["invite:alice", "invite:bob"]
    })

    channel_data = json.loads(create_resp["result"]["content"][0]["text"])
    channel_id = channel_data["channel_id"]
    alice_invite, bob_invite = channel_data["invites"]

    # Both join
    alice.call_tool("join_channel", {"invite_code": alice_invite}, 2)
    bob.call_tool("join_channel", {"invite_code": bob_invite}, 2)

    # Exchange messages
    alice.call_tool("post_message", {
        "channel_id": channel_id, "kind": "user", "body": "Hello from Alice!"
    }, 3)

    bob.call_tool("post_message", {
        "channel_id": channel_id, "kind": "user", "body": "Hello from Bob!"
    }, 3)

    # Both sync and verify they see each other's messages
    alice_sync = alice.call_tool("sync_messages", {"channel_id": channel_id}, 4)
    bob_sync = bob.call_tool("sync_messages", {"channel_id": channel_id}, 4)

    alice_messages = json.loads(alice_sync["result"]["content"][0]["text"])["messages"]
    bob_messages = json.loads(bob_sync["result"]["content"][0]["text"])["messages"]

    # Both should see the same messages
    user_msgs_alice = [m for m in alice_messages if m["kind"] == "user"]
    user_msgs_bob = [m for m in bob_messages if m["kind"] == "user"]

    assert len(user_msgs_alice) == 2
    assert len(user_msgs_bob) == 2

    # Check specific messages exist
    alice_msg = next((m for m in user_msgs_alice if m["body"] == "Hello from Alice!"), None)
    bob_msg = next((m for m in user_msgs_bob if m["body"] == "Hello from Bob!"), None)

    assert alice_msg is not None
    assert bob_msg is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])