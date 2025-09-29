# MCP Scripts

These scripts provide a simple interface for interacting with MCP multiplayer channels. They automatically handle OAuth authentication and MCP session management.

## Configuration

Edit `.env.scripts` to switch between local Docker development and remote production endpoints:

**For remote production:**
```bash
# Remote endpoint (production)
MCP_BASE_URL=https://your-domain.com

# Local endpoint (Docker development)
# MCP_BASE_URL=http://127.0.0.1:8100
```

**For local Docker development:**
```bash
# Remote endpoint (production)
# MCP_BASE_URL=https://your-domain.com

# Local endpoint (Docker development)
MCP_BASE_URL=http://127.0.0.1:8100
```

## Available Scripts

All scripts automatically use the configured endpoint and handle OAuth + MCP session management:

- **`list_channels.py`** - List all available channels with details
- **`create_channel.py`** - Create a new guessing game channel with bot
- **`join_channel.py <invite_code>`** - Join a channel using invite code
- **`session_test.py`** - Test full session continuity (create→join→message→sync)

## Usage Examples

```bash
# List channels on current endpoint
python scripts/list_channels.py

# Create a new channel
python scripts/create_channel.py

# Join a channel (use invite code from create_channel output)
python scripts/join_channel.py inv_abc123...

# Test session continuity
python scripts/session_test.py
```

## Architecture

- **`config.py`** - Environment configuration from `.env.scripts`
- **`mcp_client.py`** - Shared MCP client with OAuth and session handling

The client automatically handles:
- ✅ OAuth authentication (client registration → token generation)
- ✅ MCP session handshake (`initialize` → `notifications/initialized`)
- ✅ JSON-RPC formatting with required `params: {}` fields
- ✅ SSE response parsing for `data: ` prefixed event streams
- ✅ Error handling and connection management

## Requirements

Make sure you have the required dependencies:
```bash
pip install python-dotenv requests urllib3
```

## Testing Both Endpoints

The scripts work identically with both local Docker and remote production:

1. **Test remote** (comment out local URL in `.env.scripts`)
2. **Test local Docker** (uncomment local URL in `.env.scripts`)
3. Both endpoints share the same data and OAuth flows

This allows confident local development with the same client integration patterns that work in production.