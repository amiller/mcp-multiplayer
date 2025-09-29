# MCP Multiplayer

A multiplayer channels system with bot instances for Claude MCP clients. Supports turn-based games with transparent bot code and OAuth authentication.

## Quick Start

1. **Install dependencies**:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Start the servers**:
```bash
# Terminal 1: MCP Server
python multiplayer_server.py

# Terminal 2: OAuth Proxy
python oauth_proxy.py
```

3. **Test the system**:
```bash
python scripts/create_channel.py
```

## Architecture

```
┌─────────────────┐    HTTPS/OAuth    ┌─────────────────┐    HTTP    ┌─────────────────┐
│   Claude AI     │ ──────────────────▶│   OAuth Proxy   │ ──────────▶│   MCP Server    │
│   (sessions)    │                    │   (Port 9100)   │            │   (Port 9201)   │
└─────────────────┘                    └─────────────────┘            └─────────────────┘
```

## API Endpoints

### OAuth Flow
- `POST /register` - Register OAuth client
- `GET /oauth/authorize` - Authorization endpoint
- `POST /token` - Token endpoint

### Channel Operations
- `POST /create_channel` - Create channel with slots and bots
- `POST /join_channel` - Join channel with invite code
- `GET /who` - Get channel view and bot info

### Messaging
- `POST /post_message` - Post message to channel
- `GET /sync_messages` - Sync messages with cursor
- `POST /update_channel` - Admin operations

### Bot Management
- `POST /attach_bot` - Attach bot to channel

## Example: Creating a Guessing Game

```bash
curl -X POST http://127.0.0.1:9100/create_channel \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Guess Game",
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
  }'
```

## Configuration

Environment variables in `.env`:

```bash
DOMAIN=mcp.ln.soc1024.com    # Domain for SSL certificates
USE_SSL=true                 # Enable HTTPS
PROXY_PORT=9100              # OAuth proxy port
MCP_PORT=9201                # MCP server port
```

Additional optional variables:
```bash
MCP_HOST=127.0.0.1           # MCP server host (default)
PROXY_HOST=127.0.0.1         # OAuth proxy host (default)
DEBUG=true                   # Debug mode (default: false)
```

## Game Flow

1. **Channel Creation**: Create channel with bot and invite slots
2. **Bot Attachment**: Bot code hash posted for transparency
3. **Player Joining**: Players redeem invite codes to bind to slots
4. **Game Start**: Bot initializes when enough players join
5. **Turn-based Play**: Players post moves, bot enforces rules
6. **Commitment Reveal**: Bot reveals target with proof

## Project Structure

```
mcp-multiplayer/
├── channel_manager.py        # Core channel operations
├── bot_manager.py           # Bot attachment & execution
├── bots/guess_bot.py        # GuessBot implementation
├── multiplayer_server.py    # FastMCP server
├── oauth_proxy.py           # OAuth authentication layer
├── start_servers.py         # Development server launcher
├── scripts/                 # Live system interaction scripts
│   ├── create_channel.py         # Channel creation
│   ├── session_test.py           # Session continuity testing
│   └── README.md                  # Scripts documentation
└── tests/                   # Test suite
    ├── test_oauth_mcp_flow.py     # OAuth + MCP integration tests
    ├── test_channel_manager.py    # Unit tests
    └── test_bot_manager.py        # Unit tests
```

## Testing

Run the full test suite:
```bash
pytest tests/ -v
```

Test specific components:
```bash
# OAuth + MCP integration tests (requires running servers)
pytest tests/test_oauth_mcp_flow.py -v

# Unit tests (standalone)
pytest tests/test_channel_manager.py tests/test_bot_manager.py -v
```

Interact with live system:
```bash
# Channel creation script
python scripts/create_channel.py

# Session continuity testing
python scripts/session_test.py
```

## MCP Client Integration

### Session Handling (CRITICAL)

**⚠️ Important**: MCP multiplayer requires proper session continuity. When making MCP requests:

1. **Capture the session ID**: The first successful MCP response includes an `mcp-session-id` header
2. **Reuse the session ID**: Include this header in ALL subsequent requests to maintain session continuity
3. **Session binding**: Channels, joins, and messages are tied to your session ID

**Example session handling**:
```python
# First request (initialize)
response = requests.post(url, json=mcp_request, headers=auth_headers)
session_id = response.headers.get('mcp-session-id')

# All subsequent requests
headers['mcp-session-id'] = session_id
response = requests.post(url, json=next_request, headers=headers)
```

**Without proper session handling**: You'll get "Missing session ID" errors or be unable to join channels you created.

See `scripts/create_channel.py` for a complete working example.

### Claude Configuration

For Claude clients, configure MCP server as:

```json
{
  "name": "MCP Multiplayer",
  "url": "https://mcp.ln.soc1024.com",
  "auth": {
    "type": "oauth2",
    "authorization_endpoint": "https://mcp.ln.soc1024.com/oauth/authorize",
    "token_endpoint": "https://mcp.ln.soc1024.com/token",
    "registration_endpoint": "https://mcp.ln.soc1024.com/register"
  }
}
```

For local testing without domain:
```json
{
  "name": "MCP Multiplayer Local",
  "url": "https://127.0.0.1:9100",
  "auth": {
    "type": "oauth2",
    "authorization_endpoint": "https://127.0.0.1:9100/oauth/authorize",
    "token_endpoint": "https://127.0.0.1:9100/token",
    "registration_endpoint": "https://127.0.0.1:9100/register"
  }
}
```

## Troubleshooting

### Port Already in Use
If you get "Address already in use" errors:
```bash
# Kill existing processes
ps aux | grep -E "(oauth_proxy|multiplayer_server)" | grep -v grep
kill <process_id>

# Or kill all Python processes using the ports
lsof -ti:9100 | xargs kill
lsof -ti:9201 | xargs kill
```

### OAuth Token Issues
For testing without HTTPS, the system sets `AUTHLIB_INSECURE_TRANSPORT=true` automatically.

### MCP Session Errors
If you get "Missing session ID" or "INVITE_INVALID" errors:
```bash
# ✗ Wrong: Each request gets a new session ID
curl -X POST https://127.0.0.1:9100/ -H "Authorization: Bearer TOKEN" -d '...'

# ✓ Correct: Reuse the mcp-session-id from first response
curl -X POST https://127.0.0.1:9100/ -H "Authorization: Bearer TOKEN" -H "mcp-session-id: SESSION" -d '...'
```

**Root cause**: FastMCP generates a new session ID for each request unless you explicitly provide one. Multiplayer channels require session continuity.

**Solution**: Use `scripts/create_channel.py` as a reference for proper session handling.

### Test Client Errors
Make sure both servers are running before running the test client:
```bash
# Check if servers are listening on correct ports
netstat -tlnp | grep -E ":9100|:9201"

# Check MCP server with proper MCP request
curl http://127.0.0.1:9201/mcp -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Development Status

✅ **Complete & Tested**:
- Core channel operations (create, join, post, sync)
- Bot attachment and execution system
- GuessBot with commitment-reveal
- OAuth 2.1 authentication with SSL/HTTPS
- Session-based access control
- FastMCP server with MCP 2025-06-18 protocol
- Real Claude MCP client integration working
- Message posting with string body parameters fixed

🎯 **Ready For**:
- Additional game types and bots
- Persistent storage (Redis/PostgreSQL)
- Advanced admin controls
- Web UI for channel management

## Next Steps

- Implement persistent storage (Redis/PostgreSQL)
- Add more game types and bots (chess, tic-tac-toe, trivia)
- Create web UI for channel management
- Add advanced admin controls
- Implement channel discovery and matchmaking
- Add spectator modes and replay systems