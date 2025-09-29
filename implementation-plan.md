# MCP Multiplayer Implementation Plan

## Architecture Design

**Standalone mcp-multiplayer service** with OAuth proxy pattern from buildatool:

```
┌─────────────────┐    HTTPS/OAuth    ┌─────────────────┐    HTTP    ┌─────────────────┐
│   Claude AI     │ ──────────────────▶│   OAuth Proxy   │ ──────────▶│   MCP Server    │
│   (sessions)    │                    │   (Port 9200)   │            │   (Port 9201)   │
└─────────────────┘                    └─────────────────┘            └─────────────────┘
```

## Key Design Decisions

**Session → Slot Binding**: Invite codes are one-time tokens that bind a Claude session to a specific channel slot. Once redeemed, the session gets a durable binding (no explicit member_token needed).

**In-Memory Storage**:
- Channels, slots, messages, bot instances all in memory
- Simple Python dicts with threading locks
- Bot state as JSON blobs per `(channel_id, bot_id)`

**OAuth Layer**: Reuse buildatool's patterns but simplified - just need to extract session IDs from Claude clients and pass them through.

## Implementation Structure

```
mcp-multiplayer/
├── oauth_proxy.py          # OAuth + SSL proxy (port 9200)
├── multiplayer_server.py   # Main MCP server (port 9201)
├── channel_manager.py      # Channel CRUD operations
├── bot_manager.py          # Bot attachment & execution
├── bots/
│   └── guess_bot.py       # GuessBot implementation
├── .env.example           # Config template
└── requirements.txt       # Dependencies
```

## Core Data Models

**Channel State**:
```python
{
  "channel_id": "chn_123",
  "name": "Guess Demo",
  "slots": [
    {"slot_id": "s0", "kind": "bot", "filled_by": "bot:GuessBot", "admin": True},
    {"slot_id": "s1", "kind": "invite", "filled_by": "sess_abc", "admin": False},
    {"slot_id": "s2", "kind": "invite", "filled_by": None, "admin": False}
  ],
  "messages": [Message, ...],
  "bots": {bot_id: BotInstance}
}
```

**Invite → Session Flow**:
1. `create_channel()` → generates invite codes for `invite:*` slots
2. `join_channel(invite_code)` → binds session to slot
3. All subsequent API calls use session ID for auth

## Testing Plan

### Layer 1: Channel Logic Tests (`test_channel_manager.py`)

**Channel CRUD**:
```python
def test_create_channel():
    # Basic creation with slots
    # Invite code generation
    # Slot validation (bot vs invite slots)

def test_join_channel():
    # Valid invite redemption → session binding
    # Duplicate joins (idempotent)
    # Invalid/expired invites
    # Slot already filled

def test_channel_membership():
    # Session permissions per slot
    # Admin vs regular slot privileges
    # Slot binding persistence
```

**Messaging**:
```python
def test_post_message():
    # Valid session posting
    # Message ordering/IDs
    # Non-member posting rejection
    # Message kinds (user/bot/system/control)

def test_sync_messages():
    # Cursor-based pagination
    # Long-poll timeout behavior
    # Empty channel sync
    # ChannelView updates when composition changes
```

**Admin Operations**:
```python
def test_update_channel():
    # set_bot, remove_bot operations
    # yield_slot (bot ↔ invite)
    # set_admin privileges
    # Non-admin rejection
    # System message generation
```

### Layer 2: GuessBot Tests (`test_guess_bot.py`)

**Game Lifecycle**:
```python
def test_bot_initialization():
    # on_init: commitment, prompt, state posting
    # Target selection and commitment hash
    # Initial state structure

def test_player_joining():
    # on_join: player registration
    # Game start when quorum reached
    # Turn order establishment

def test_turn_management():
    # Valid turn enforcement
    # Turn violations (wrong session)
    # Turn timeouts
    # Turn advancement
```

**Game Logic**:
```python
def test_guess_processing():
    # Valid guesses: high/low/correct responses
    # Invalid values/formats
    # Out-of-turn moves rejection
    # State version increments

def test_game_ending():
    # Correct guess handling
    # Commitment reveal and verification
    # Game state finalization
```

### Integration Layer (`test_integration.py`)

**Bot Attachment**:
```python
def test_attach_bot_to_channel():
    # Manifest posting to channel
    # Bot instance creation
    # Code hash generation
    # Hook registration

def test_bot_message_dispatch():
    # User messages → bot.on_message()
    # Bot responses posted to channel
    # State persistence across calls
```

## Test Structure

```
tests/
├── test_channel_manager.py    # Pure channel logic
├── test_guess_bot.py         # Bot behavior in isolation
├── test_integration.py       # Bot + channel integration
├── fixtures/
│   ├── sample_channels.py    # Test data
│   └── mock_bots.py         # Simple test bots
└── conftest.py              # Pytest setup
```

**Test Approach**: Each layer tests independently with mocks, then integration tests verify the full flow.

## Implementation Order

1. **Channel Manager** - Core channel operations
2. **Bot Manager** - Bot attachment and execution
3. **GuessBot** - Specific game implementation
4. **MCP Server** - FastMCP endpoints
5. **OAuth Proxy** - Authentication layer
6. **Integration Tests** - End-to-end validation