# Scripts Directory

Scripts for interacting with running MCP multiplayer instances.

## Scripts

- **`create_channel.py`** - Channel creation script that follows Claude's exact MCP pattern
  - Uses proper MCP session initialization flow
  - Connects to https://mcp.ln.soc1024.com
  - Successfully creates channels with invite codes

- **`list_channels.py`** - Lists channels and their status
  - Demonstrates channel discovery and inspection

- **`browser_test.py`** - Browser-compatible channel testing
  - Tests channel operations from browser perspective

- **`session_test.py`** - Session continuity testing
  - Tests MCP session handling through OAuth proxy
  - Demonstrates session continuity issues and fixes

## Usage

All scripts connect to the production domain at https://mcp.ln.soc1024.com (which routes to localhost:9100 with SSL).

Ensure both servers are running:
```bash
# Terminal 1: MCP Server
python multiplayer_server.py

# Terminal 2: OAuth Proxy
PROXY_PORT=9100 USE_SSL=true DOMAIN=mcp.ln.soc1024.com python oauth_proxy.py
```

Then run any script:
```bash
python scripts/create_channel.py
```

## Key Pattern (from create_channel.py)

The working pattern bypasses OAuth complexity and follows Claude's exact MCP flow:

1. **Initialize MCP session**
2. **Send initialized notification**
3. **Call tools with proper session headers**

This pattern successfully creates channels that Claude can join.