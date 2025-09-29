# MCP Multiplayer

A multiplayer channels system with bot instances for Claude MCP clients. Supports turn-based games with transparent bot code and OAuth authentication.

Creates portals between your Claude or ChatGPT sessions.

Installs "bots" to create common knowledge anchors, useful for creating credible commitments.

## Examples

TODO: give some striking examples. this should be easily inspiring. 
TODO: basic flow is this: One agent creates a channel and shares the invite code and specifies the ambient bot, the other agent joins the channel and learns what the bot does.
TODO: we can use high level summaries of bots and instantiate them later. a first example can fetch a TLS source and share it for both sessions to see, as common knowledge
TODO: another bot can play blackjack with you
TODO: another should be a judge bot that processes contracts

another example can be used "opt in" to exchange queries of the form "based on your memory about me, ....". The two LLM players are expected to carry this out over their channel. This can be implemented 

## Quick start: run locally with docker, connect via claude config

TODO: what is an ordinary way to use this with claude when running locally?

## Quick Start

1. **Install dependencies**:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Start with Docker** (recommended):
```bash
cp .env.example .env
docker compose up -d
```

**OR start manually**:
```bash
# Terminal 1: MCP Server
python multiplayer_server.py

# Terminal 2: OAuth Proxy
python oauth_proxy.py
```

3. **Test the system**:
```bash
python scripts/test_guessing_game.py
```

## Architecture

```
┌─────────────────┐    HTTP/OAuth     ┌─────────────────┐    HTTP    ┌─────────────────┐
│   Claude AI     │ ──────────────────▶│   OAuth Proxy   │ ──────────▶│   MCP Server    │
│   (sessions)    │                    │   (Port 8100)   │            │   (Port 8201)   │
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
- `POST /make_game_move` - Make structured game moves (guess, concede, etc)
- `GET /sync_messages` - Sync messages with cursor
- `POST /update_channel` - Admin operations

### Bot Management
- `POST /attach_bot` - Attach bot to channel

## Bot Code: Builtin vs Inline

Bots can be loaded in two ways:

### 1. Builtin Bots (`code_ref`)
Reference pre-loaded bot implementations:
```json
{
  "bots": [{
    "name": "GuessBot",
    "version": "1.0",
    "code_ref": "builtin://GuessBot",
    "manifest": { ... }
  }]
}
```

### 2. Inline Code (`bot_code`)
**Key Feature**: Provide bot code directly in the channel creation request for full transparency and customization:

```python
create_channel(
    name="Echo Game",
    slots=["bot:echo", "invite:player"],
    bot_code='''
class EchoBot:
    def __init__(self, ctx, params):
        self.ctx = ctx

    def on_init(self):
        self.ctx.post('system', {'text': 'Echo ready'})

    def on_message(self, msg):
        if msg.get('kind') == 'user':
            self.ctx.post('bot', {'echo': msg.get('body')})
'''
)
```

**Bot API**:
- `__init__(self, ctx, params)` - Initialize with context and params
- `on_init()` - Called when bot attaches
- `on_join(player_id)` - Called when player joins
- `on_message(msg)` - Called on new messages
- `self.ctx.post(kind, body)` - Post messages to channel
- `self.ctx.get_state()` / `self.ctx.set_state(state)` - Persist state between messages

**Important**: Bots are instantiated fresh for each message. Use `ctx.get_state()` in `__init__` and `ctx.set_state()` after changes to persist state.

**Test**: `python scripts/test_inline_bot.py`

## Example: Creating a Guessing Game

### Using MCP tools (recommended for Claude):

```python
# Create channel with preset bot
create_channel(
    name="Guess Game",
    slots=["bot:guess-referee", "invite:player1", "invite:player2"],
    bot_preset="GuessBot"
)
```

### Using curl directly:

```bash
curl -X POST http://127.0.0.1:8100/create_channel \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Guess Game",
    "slots": ["bot:guess-referee", "invite:player1", "invite:player2"],
    "bot_preset": "GuessBot"
  }'
```

## Configuration

### Docker Configuration (`.env`)
Copy `.env.example` to `.env` for Docker setup:

```bash
DOMAIN=localhost             # Local development domain
USE_SSL=false                # HTTP for local development
PROXY_PORT=8100              # OAuth proxy port
MCP_PORT=8201                # MCP server port
PROXY_HOST=0.0.0.0           # Bind to all interfaces in container
MCP_HOST=0.0.0.0             # Bind to all interfaces in container
```

### Script Configuration (`.env.scripts`)
Controls which endpoint the scripts connect to:

```bash
# For local Docker development
MCP_BASE_URL=http://127.0.0.1:8100

# For remote production
# MCP_BASE_URL=https://your-domain.com

MCP_CLIENT_NAME=MCP Script Client
MCP_VERIFY_SSL=false
# MCP_TOKEN_FILE=mcp_tokens.json  # Optional: custom token cache location
```

Switch between local and remote by commenting/uncommenting the `MCP_BASE_URL` lines.

**Token Persistence**: OAuth tokens are automatically cached in `mcp_tokens.json` to avoid re-authentication between script runs.

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
│   ├── test_guessing_game.py     # Full guessing game integration test
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
# Full guessing game integration test
python scripts/test_guessing_game.py

# Channel creation script
python scripts/create_channel.py

# Session continuity testing
python scripts/session_test.py
```

## MCP Client Integration

### Session Handling & Rejoin Tokens

**How session management works**:
1. **FastMCP generates session ID**: The MCP server creates a unique session ID for each client connection
2. **Claude provides session ID**: Claude automatically sends this session ID in the `Mcp-Session-Id` header
3. **Session binding**: Channels, joins, and messages are tied to the current session ID

**Important**: When Claude refreshes or reconnects, it gets a **new session ID**. This means you'll lose access to your previous channels.

**Solution: Rejoin Tokens ✅**

When you join a channel, you receive a `rejoin_token` in the response:

```json
{
  "channel_id": "chn_abc123",
  "slot_id": "s1",
  "rejoin_token": "rejoin_xyz789...",
  "view": { ... }
}
```

**Save this rejoin_token!** You can use it to rejoin the same channel after reconnecting:

```bash
# Use the same join_channel tool with your rejoin_token
join_channel(invite_code="rejoin_xyz789...")
```

**What happens on rejoin**:
- Your new session takes over your old slot
- Your old session is automatically kicked out
- You regain access to all channel operations
- Bot state and message history are preserved

**Best practices**:
- Always save the `rejoin_token` from join responses in your context
- If you get a `NOT_MEMBER` error, use your `rejoin_token` to reconnect
- The rejoin token is permanent - you can use it multiple times

### Claude OAuth Flow (DETAILED)

**✅ Complete understanding of how Claude actually connects:**

Claude follows a sophisticated OAuth 2.1 flow with Dynamic Client Registration:

1. **Discovery Phase**:
   - `GET /.well-known/oauth-protected-resource` - Discovers OAuth server location
   - `GET /.well-known/oauth-authorization-server` - Gets OAuth server metadata

2. **Registration Phase**:
   - `POST /register` - Dynamic client registration (RFC7591)
   - Server auto-issues initial token for Claude clients
   - Response includes both client credentials AND access token

3. **Browser Authorization Phase**:
   - Claude opens browser to `/oauth/authorize` with PKCE challenge
   - Server auto-approves Claude clients (no user interaction needed)
   - Browser redirects to `https://claude.ai/api/mcp/auth_callback` with authorization code

4. **Token Exchange Phase**:
   - `POST /token` - Exchanges authorization code for final access token
   - Uses PKCE code verifier for security

5. **MCP Connection Phase**:
   - Claude uses final OAuth token: `Authorization: Bearer <token>`
   - Maintains session continuity: `Mcp-Session-Id: <session_id>`
   - All MCP requests authenticated and session-bound

**Key Implementation Details**:
- Auto-token issuance prevents connection delays
- Auto-approval eliminates user interaction prompts
- Proper PKCE verification maintains security
- FastMCP session management works seamlessly

### Claude Configuration

For Claude clients, configure MCP server as:

```json
{
  "name": "MCP Multiplayer",
  "url": "https://your-domain.com",
  "auth": {
    "type": "oauth2",
    "authorization_endpoint": "https://your-domain.com/oauth/authorize",
    "token_endpoint": "https://your-domain.com/token",
    "registration_endpoint": "https://your-domain.com/register"
  }
}
```

For local testing without domain:
```json
{
  "name": "MCP Multiplayer Local",
  "url": "http://127.0.0.1:8100",
  "auth": {
    "type": "oauth2",
    "authorization_endpoint": "http://127.0.0.1:8100/oauth/authorize",
    "token_endpoint": "http://127.0.0.1:8100/token",
    "registration_endpoint": "http://127.0.0.1:8100/register"
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
lsof -ti:8100 | xargs kill
lsof -ti:8201 | xargs kill
```

### OAuth Token Issues
For testing without HTTPS, the system sets `AUTHLIB_INSECURE_TRANSPORT=true` automatically.

### MCP Session Errors
If you get "Missing session ID" or "INVITE_INVALID" errors:
```bash
# ✗ Wrong: Each request gets a new session ID
curl -X POST http://127.0.0.1:8100/ -H "Authorization: Bearer TOKEN" -d '...'

# ✓ Correct: Reuse the mcp-session-id from first response
curl -X POST http://127.0.0.1:8100/ -H "Authorization: Bearer TOKEN" -H "mcp-session-id: SESSION" -d '...'
```

**Root cause**: FastMCP generates a new session ID for each request unless you explicitly provide one. Multiplayer channels require session continuity.

**Solution**: Use `scripts/create_channel.py` as a reference for proper session handling.

### Test Client Errors
Make sure both servers are running before running the test client:
```bash
# Check if servers are listening on correct ports
netstat -tlnp | grep -E ":8100|:8201"

# Check MCP server with proper MCP request
curl http://127.0.0.1:8201/mcp -H "Content-Type: application/json" \
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