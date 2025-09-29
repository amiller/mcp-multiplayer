#!/usr/bin/env python3
"""
Shared MCP client functionality for all scripts
"""

import json
import requests
import base64
import os
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from config import get_base_url, get_client_name, should_verify_ssl, get_token_file

disable_warnings(InsecureRequestWarning)

class MCPClient:
    def __init__(self):
        self.base_url = get_base_url()
        self.client_name = get_client_name()
        self.verify_ssl = should_verify_ssl()
        self.token_file = get_token_file()
        self.token = None
        self.headers = None

    def _load_token(self):
        """Load token from file if it exists"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    if data.get('base_url') == self.base_url:
                        self.token = data.get('access_token')
                        return True
            except (json.JSONDecodeError, KeyError):
                pass
        return False

    def _save_token(self, token):
        """Save token to file"""
        dirname = os.path.dirname(self.token_file)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(self.token_file, 'w') as f:
            json.dump({
                'base_url': self.base_url,
                'access_token': token
            }, f)

    def get_oauth_token(self):
        """Get OAuth token for authentication"""
        # Try loading from file first
        if self._load_token():
            return self.token

        # Register client
        reg_resp = requests.post(f'{self.base_url}/register', json={
            'client_name': self.client_name,
            'redirect_uris': ['http://localhost/callback']
        }, verify=self.verify_ssl)

        if reg_resp.status_code != 201:
            raise Exception(f"Registration failed: {reg_resp.status_code} {reg_resp.text}")

        client_data = reg_resp.json()
        creds = base64.b64encode(f'{client_data["client_id"]}:{client_data["client_secret"]}'.encode()).decode()

        # Get token
        token_resp = requests.post(f'{self.base_url}/token',
            data={'grant_type': 'client_credentials', 'scope': 'mcp'},
            headers={'Authorization': f'Basic {creds}'},
            verify=self.verify_ssl)

        if token_resp.status_code != 200:
            raise Exception(f"Token request failed: {token_resp.status_code} {token_resp.text}")

        self.token = token_resp.json()['access_token']
        self._save_token(self.token)
        return self.token

    def initialize_session(self):
        """Initialize MCP session with proper handshake"""
        if not self.token:
            raise Exception("No OAuth token available. Call get_oauth_token() first.")

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
                "capabilities": {"tools": {"listChanged": True}},
                "clientInfo": {"name": self.client_name, "version": "1.0.0"}
            }
        }

        resp = requests.post(f"{self.base_url}/", json=init_payload, headers=headers, verify=self.verify_ssl)
        if resp.status_code != 200:
            raise Exception(f"Initialize failed: {resp.status_code} {resp.text}")

        session_id = resp.headers.get('mcp-session-id')
        headers['mcp-session-id'] = session_id

        # Send initialized notification
        notify_payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        requests.post(f"{self.base_url}/", json=notify_payload, headers=headers, verify=self.verify_ssl)

        self.headers = headers
        return headers

    def call_tool(self, tool_name, arguments=None, request_id=2):
        """Call an MCP tool"""
        if not self.headers:
            raise Exception("No session initialized. Call initialize_session() first.")

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }

        resp = requests.post(f"{self.base_url}/", json=payload, headers=self.headers, verify=self.verify_ssl)

        # Parse SSE response
        if resp.status_code == 200:
            for line in resp.text.split('\n'):
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'result' in data and 'content' in data['result']:
                            content = data['result']['content'][0]['text']
                            return json.loads(content)
                        elif 'error' in data:
                            raise Exception(f"Tool error: {data['error']['message']}")
                    except json.JSONDecodeError:
                        continue

        raise Exception(f"Tool call failed: {resp.status_code} {resp.text}")

    def list_tools(self):
        """List available tools"""
        if not self.headers:
            raise Exception("No session initialized. Call initialize_session() first.")

        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        resp = requests.post(f"{self.base_url}/", json=payload, headers=self.headers, verify=self.verify_ssl)

        if resp.status_code == 200:
            for line in resp.text.split('\n'):
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'result' in data:
                            return data['result']['tools']
                    except json.JSONDecodeError:
                        continue

        raise Exception(f"List tools failed: {resp.status_code} {resp.text}")

    def connect(self):
        """Full connection flow: OAuth + session initialization"""
        print(f"Connecting to {self.base_url}...")
        if self._load_token():
            print("Using cached OAuth token")
        else:
            self.get_oauth_token()
            print("OAuth token obtained and cached")
        self.initialize_session()
        print("MCP session initialized")
        return self