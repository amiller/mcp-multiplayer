#!/usr/bin/env python3
"""
Fetch and display MCP tool documentation from a server
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import MCPClient
from config import print_config

def fetch_tools():
    """Fetch tool list and display documentation"""
    print_config()
    print()

    client = MCPClient()
    client = client.connect()

    # Make raw MCP request for tools/list
    import requests
    response = requests.post(
        f'{client.base_url}/',
        json={'jsonrpc': '2.0', 'id': 'tools', 'method': 'tools/list', 'params': {}},
        headers=client.headers
    )

    # Parse SSE response
    for line in response.text.split('\n'):
        if line.startswith('data: '):
            data = json.loads(line[6:])
            if 'result' in data:
                tools = data['result']['tools']
                print(f"\nFound {len(tools)} tools:\n")
                print("=" * 80)

                for tool in tools:
                    print(f"\n{tool['name']}")
                    print("-" * 80)
                    if 'description' in tool:
                        print(tool['description'])
                    if 'inputSchema' in tool:
                        print(f"\nInput Schema:")
                        print(json.dumps(tool['inputSchema'], indent=2))
                    print()

if __name__ == "__main__":
    fetch_tools()