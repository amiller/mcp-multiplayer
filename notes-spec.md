# Session Plan — Channels + Bot Instances (Guessing Game MVP)

> **v0 ULTRA‑SIMPLE SPEC** — demo‑trust model. No hashes, no commitments. Invitees must be able to see exactly which bots are running and what they do. Minimal CRUD. One page of endpoints.

---

## 1) Channel creation (with visible bots)

**create_channel(name, slots, bots=[]) → {channel_id, invites:[...], view: ChannelView}**

* `slots`: array like `["bot:guess-referee", "invite:player", "invite:player"]` (order can imply turn order if the bot uses it).
* `bots`: array of **BotDef** that map to any `bot:*` slots.
* Returns **invite codes** for each `invite:*` slot and a `ChannelView` describing bots.
* Server also posts a `system {type:"bots_announced"}` message for visibility.

**BotDef (what clients provide at creation)**

```json
{
  "slot": "bot:guess-referee",
  "name": "GuessBot",
  "version": "0.1",
  "inline_code": "...optional python...",
  "code_ref": "tool://dynamic_toolbox/GuessBot",
  "manifest": {
    "summary": "Turn-based number guessing referee",
    "hooks": ["on_init", "on_join", "on_post"],
    "emits": ["prompt", "state", "turn", "judge"],
    "params": {"mode":"number","range":[1,100],"timeout_s":600}
  },
  "env_redacted": {"API_KEY?": "<sealed-blob>"}
}
```

**Trust model**: demo mode — bots are trusted code; no hashes.

---

## 2) Joining & seeing what's running

**join_channel(invite_code) → {channel_id, slot_id, member_token, view: ChannelView}**

* On join, client gets the current **ChannelView** that **explicitly lists bots**.

**who(channel_id) → ChannelView** *(any member)*

* Lightweight read to show everyone (and every bot) in the room.

**ChannelView**

````json
{
  "channel_id": "chn_123",
  "name": "Guess Demo",
  "slots": [
    {"slot_id":"s0","kind":"bot","label":"guess-referee","filled_by":"bot:GuessBot@0.1","role":"referee","admin":true},
    {"slot_id":"s1","kind":"invite","label":"player A","filled_by":null,"role":"player","admin":false},
    {"slot_id":"s2","kind":"invite","label":"player B","filled_by":null,"role":"player","admin":false}
  ],
  "bots": [
    {"slot_id":"s0","name":"GuessBot","version":"0.1","manifest":{"summary":"Turn-based number guessing referee","hooks":["on_init","on_join","on_post"],"emits":["prompt","state","turn","judge"],"params":{"mode":"number","range":[1,100],"timeout_s":600}}}
  ]
}```

Server also posts a **system message** at creation:
```json
{"kind":"system","body":{"type":"bots_announced","bots":[{"slot_id":"s0","name":"GuessBot","version":"0.1","summary":"Turn-based number guessing referee"}]}}
````

---

## 3) Minimal messaging / sync (self‑contained)

To keep the spec tiny and async-friendly, merge reads into a single **sync** endpoint.

* **post(channel_id, member_token, body) → {msg_id}**
* **sync(channel_id, member_token, cursor: int | null, timeout_ms: int = 25000) → {messages:[...], cursor:int, view: ChannelView | null}**

  * `cursor` is the last seen message id; returns any new messages after it.
  * Long‑poll up to `timeout_ms`; returns early if messages arrive.
  * `view` is included only when the channel composition changed since last cursor.

**Message**: `{id, channel_id, sender:"sess_X"|"bot:GuessBot", kind:"user"|"bot"|"system", body:{...}, ts}`

---

## 4) Micro‑CRUD (admin only; can be a bot)

**update_channel(channel_id, member_token_admin, ops[]) → {ok, view}**
Allowed ops (minimal):

* `set_bot(slot_id, BotDef)` — replace bot or its params; server re‑announces.
* `remove_bot(slot_id)` — clear a bot slot.
* `yield_slot(slot_id, to: "bot"|"invite", bot?: BotDef)` — swap who controls the slot.
* `set_admin(slot_id, admin: bool)` — promote/demote.
* `rename(name)` — rename channel.

Every change emits a `system` message (e.g., `{type:"bot_changed", slot_id:"s0"}`).

**Access model**

* Joining a `invite:*` slot issues a `member_token` bound to that slot.
* Any slot with `admin:true` (bot or invite that becomes a member) can call `update_channel`.

---

## 5) Guessing Game (super short rules)

* Bot in referee slot:

  * `on_init` → posts `prompt` + initial `state` + first `turn`.
  * `on_post(user move)` → if it’s that user’s turn and value is valid: reply `judge: high|low|correct`, then advance `turn`.
  * On `correct` → post `reveal` and `end`.

**Player move**: `post(..., {type:"move", game:"guess", value: 73})`

**Bot replies**: `{kind:"bot", body:{type:"judge", result:"high|low|correct"}}`, then `{kind:"bot", body:{type:"turn", player:"sess_B"}}`.

---

## 6) Redacted env (still simple)

* `env_redacted` accepted at `create_channel` or in `set_bot`.
* Never returned on reads; injected only into the bot runtime.
* Optional egress guard: block known secret keys from being posted verbatim.

---

## 7) Client guidance

* After join (or on first `sync`), render `ChannelView.bots` so members know which bots are active and what they do.
* Post moves only when the bot indicates it’s your turn (if the bot enforces turns).
* Use `sync` with a rolling `cursor` for near‑realtime updates.

---

## 8) Minimal errors & auth (one box)

* **Errors**: `INVITE_INVALID`, `NOT_MEMBER`, `NOT_ADMIN`, `BAD_OP`, `RATE_LIMIT`, `TIMEOUT`.
* **Auth**: capability tokens only — `invite_code` (one‑shot) → `member_token` (scoped to slot). No user accounts.

---

## 9) Inline GuessBot stub (drop‑in demo)

```python
# Minimal referee bot (number mode)
class GuessBot:
    def __init__(self, ctx, params):
        self.ctx = ctx
        lo, hi = params.get('range', [1,100])
        self.target = params.get('target') or __import__('random').randint(lo, hi)
        self.players = []
        self.turn = 0
        self.range = (lo, hi)

    def on_init(self):
        self.ctx.post({"kind":"bot","body":{"type":"prompt","text":f"Guess a number {self.range[0]}..{self.range[1]}"}})
        self.ctx.post({"kind":"bot","body":{"type":"state","players":self.players}})

    def on_join(self, session_id):
        if session_id not in self.players:
            self.players.append(session_id)
        if len(self.players) == 2:
            self.ctx.post({"kind":"bot","body":{"type":"turn","player":self.players[self.turn]}})

    def on_post(self, msg):
        if msg.get('kind') != 'user':
            return
        body = msg.get('body', {})
        if body.get('type') != 'move':
            return
        player = self.players[self.turn]
        if msg.get('sender') != player:
            return  # not your turn
        val = int(body.get('value'))
        if val == self.target:
            self.ctx.post({"kind":"bot","body":{"type":"judge","result":"correct"}})
            self.ctx.post({"kind":"system","body":{"type":"end"}})
            return
        self.ctx.post({"kind":"bot","body":{"type":"judge","result":"high" if val>self.target else "low"}})
        self.turn = 1 - self.turn
        self.ctx.post({"kind":"bot","body":{"type":"turn","player":self.players[self.turn]}})
```

---

## 10) That’s it

* Types are only `bot` and `invite`.

* Five endpoints: `create_channel`, `join_channel`, `post`, `sync`, `update_channel`.

* ChannelView always exposes bots so members see what’s running.

* 5 endpoints, one data shape, zero hashes. Transparent to invitees by design.

## BotSpec (what clients provide at channel creation)

```json
{
  "name": "guess-bot",
  "version": "0.1.0",
  "inline_code": "...python..." | null,
  "code_ref": "tool://dynamic_toolbox/guess_bot@abcdef" | null,
  "manifest": {
    "hooks": ["on_init", "on_join", "on_post"],
    "emits": ["prompt", "state", "turn", "judge"],
    "state_public_schema": {"type": "object"},
    "needs_env": ["API_KEY?", "SECRET_SALT?"],
    "permissions": {"can_update_channel": false}
  },
  "params": {"mode": "number", "range": [1,100], "timeout_s": 600}
}
```

* **Code**: either `inline_code` (embedded source) or `code_ref` (already‑known tool). Server computes and posts `code_hash`.
* **Redacted env**: keys in `needs_env` may be supplied via `bot_env_redacted`; server decrypts into the bot’s context only.
* **Permissions**: if `can_update_channel` is true **and** the slot is `admin`, the bot may perform admin actions.

---

## Access control (by slot)

* Each filled slot (human or bot) has a **capability token** (member_token). Actions allowed:

  * **human slot**: `post`, view messages, view public channel state.
  * **bot slot**: in addition, receive `on_*` hooks and may `post` automations.
  * **admin slot** (human *or* bot): may **update_channel**.

**update_channel(channel_id, member_token, ops[]) → {ok}**
Allowed ops (authorised only if caller is admin):

* `set_bot(slot_id, BotSpec)` — replace bot code/params; posts new `code_hash`.
* `debug_bot(slot_id, action, payload)` — see Debug below.
* `yield_control(from_slot, to="bot|human")` — flip slot kind (keeps role/admin flag).
* `set_admin(slot_id, admin: bool)` — promote/demote.
* `set_env_redacted(keys...)` — rotate or add sealed env items.

---

## Debug surface (admin‑only)

* `debug_bot(slot_id, action, payload)` where action ∈ {

  * `inspect_state` → returns public + private sizes/keys (no secrets),
  * `replace_state` (surgical patch),
  * `emit_hook` (e.g., replay `on_post` with a given message),
  * `toggle_pause` (stop processing),
  * `tail_logs` (bounded window),
    }
    All debug events are posted to the channel as `control:debug` messages for audit.

---

## Guessing Game on this model (minimal)

* Channel created with **three slots**: `{bot: referee, admin:true}`, `{human player A}`, `{human player B}`.
* Bot `on_init` picks target, posts commitment hash, emits `prompt`, emits first `turn`.
* Players `post({move:"guess", value: N})` only on their turn; bot replies with `judge` and then `turn`.
* On correct guess, bot reveals `(target, nonce)`; server verifies `sha256(target||nonce) == commit` and posts `verified: true`.

---

## Redaction model (practical)

* `bot_env_redacted` is stored encrypted (server key) and **never** returned in any read.
* At bot runtime, env is injected into the bot context (e.g., `ctx.env["API_KEY"]`).
* If bot tries to post secrets, server applies simple **egress guard** (deny keys labelled as secret; allow hashes/last‑4 display).

---

## Types (concise)

```json
ChannelView = {
  "channel_id": "chn_...",
  "name": "...",
  "slots": [
    {"slot_id":"s1","kind":"bot|human","role":"referee|player|observer","admin":true|false,
     "filled_by":"sess_..."|"bot:guess-bot"|null,
     "bot": {"name":"...","version":"...","code_hash":"sha256:..."}|null}
  ],
  "created_at": "..."
}

Message = {"id":123,"channel_id":"chn","sender":"sess_X|bot:guess-bot","body":{...},"ts":"..."}
```

---

## Why this is simpler

* One **create** call defines the whole room **and** which bots run where.
* Slots are the only authority boundary you need.
* Admin can mutate anything later via a single `update_channel` entrypoint.
* Redaction is opt‑in and scoped to bots.

---

# Session Plan — Channels + Bot Instances (Guessing Game MVP)

Goal: minimal, composable interface that layers a turn‑based guessing game on top of a basic channel. Keep it dead simple, capability‑based, and easy to extend to other games.

---

## 0) Mental model

* **Channel** = shared mailbox with ordered messages; created by one session, joined via invite capabilities.
* **Bot Instance** = code + state attached to a channel; its code hash + manifest become **common knowledge** by being posted in‑channel.
* **Players** = sessions joined to the channel. The bot enforces turns and rules.

---

## 1) Channel Core (MVP)

**Interfaces**

* `create_channel(name: str, invites: int = 2) -> {channel_id, invites: [invite_code...]}`
* `join_channel(invite_code: str) -> {channel_id, session_id}`
* `post_message(channel_id: str, kind: str, body: object) -> {msg_id, ts}`
* `get_messages(channel_id: str, since_id: int = 0, limit: int = 100) -> [Message]`
* `wait_for_message(channel_id: str, since_id: int, timeout_ms: int = 25000) -> [Message]`

**Message**

```json
{
  "id": 42,
  "channel_id": "chn_...",
  "session_id": "sess_...",
  "kind": "user|bot|control|system",
  "body": {"...": "..."},
  "ts": "2025-09-28T17:12:00Z"
}
```

**Notes**

* Capability invites (bearer tokens). After `join`, issue a durable `member_token` for continued access.
* Long‑poll for near‑realtime; no websockets needed.

---

## 2) Bot Instances (Composable)

**Attach a bot to a channel**

* `attach_bot(channel_id, name, code_ref|inline_code, manifest, params?) -> {bot_id, code_hash, manifest}`

  * `code_hash` posted to channel as a `control` message → common knowledge.
  * `manifest`: declares message hooks, game type, and any commands the bot may emit.

**Bot manifest (minimal)**

```json
{
  "name": "guess-bot",
  "version": "0.1.0",
  "hooks": ["on_channel_init", "on_player_join", "on_message"],
  "emits": ["bot:prompt", "bot:state", "bot:turn", "bot:judge"],
  "state_schema": {"type": "object"}
}
```

**Bot lifecycle (per channel instance)**

1. `on_channel_init` ⇒ emit `bot:prompt` (welcome/instructions) and `bot:state` (initial state snapshot).
2. `on_player_join(session_id)` ⇒ register player, maybe start game when quorum met.
3. `on_message(kind:user)` ⇒ process moves; emit judgments/turn changes.

**Persistence**

* Bot state is a JSON blob keyed by `(channel_id, bot_id)`.
* Every bot emission includes `state_version` to support optimistic concurrency.

---

## 3) Guessing Game (MVP rules)

**Game**: Hidden target; players alternate guessing. Bot gives graded feedback and enforces turns. Works with numbers, words, or categories.

**Setup**

* Bot param: `{ "mode": "number|word", "range": [1,100], "turn_order": "join_order|random" }`
* Bot picks target on `on_channel_init` and stores a commitment: `commit = H(target || nonce)`; posts `commit` to the channel (prevents cheating). Reveals `(target, nonce)` at end.

**Turns**

* `bot:turn` message announces whose turn it is and a soft timeout (e.g., 10 minutes). If timeout passes, bot can auto‑pass or apply penalty.

**Moves (player messages)**

```json
{"kind": "user", "body": {"move": "guess", "value": 73}}
{"kind": "user", "body": {"move": "concede"}}
```

**Bot responses**

```json
{"kind": "bot", "body": {"type": "judge", "result": "high|low|correct|invalid", "hint": "within 10"}}
{"kind": "control", "body": {"type": "bot:turn", "player": "sess_...", "deadline": "..."}}
{"kind": "control", "body": {"type": "bot:state", "state_version": 3, "public_state": {"round": 4, "history": [...]}}}
```

**Ending**

* On `correct`, bot reveals `(target, nonce)` and posts verification: `H(target||nonce) == commit`.

**Variants**

* *Word mode*: return similarity hints (e.g., length match, letter overlap count) instead of high/low.
* *Hot/Cold*: numeric distance bands.
* *Multi‑agent spell‑cast layer*: accepted “challenge” messages can alter the next response style (e.g., reverse spelling) without affecting core guessing logic.

---

## 4) Minimal bot code contract (pseudo‑API)

Bots run in the same MCP process and receive events via a small adapter. The adapter posts into the channel using `post_message`.

```python
class GuessBot:
    def __init__(self, channel_id, params):
        self.state = {...}

    def on_channel_init(self, ctx):
        ctx.post("bot:prompt", {"text": "Guess the number 1..100"})
        ctx.post("bot:state", {"public_state": {...}})

    def on_player_join(self, ctx, session_id):
        # register player; maybe start
        ...

    def on_message(self, ctx, msg):
        if msg.kind != "user":
            return
        move = msg.body.get("move")
        ... # validate turn, judge, update state
        ctx.post("bot:judge", {"result": ...})
        ctx.post("bot:turn", {"player": next_player, "deadline": ...})
```

**Adapter responsibilities**

* Load bot, keep `(channel_id, bot_id)` state.
* Dispatch hooks for incoming channel messages.
* Provide `ctx.post(kind, body)` that wraps `post_message(...)` and appends `bot_id`, `state_version`.

---

## 5) Client guidance (to make agents play along)

* When a client joins a channel, it should:

  1. Read `bot:prompt` and `bot:state` messages to establish rules.
  2. Obey `bot:turn` (only send `move` when it’s your turn).
  3. If "spell‑cast" constraints are posted, rewrite its next reply accordingly.

---

## 6) Error handling / edge cases

* Duplicate joins → idempotent success.
* Turn violations → bot responds with `invalid` without advancing turn.
* Timeouts → auto‑pass or penalty per bot param.
* State races → reject writes with stale `state_version`.

---

## 7) Why this is composable

* The **channel** API never changes.
* Each **game** is a new bot with its own manifest and message dialect.
* The **common knowledge** property arises from posting the bot’s `code_hash` + manifest at attach‑time.

---

## 8) Next steps

1. Implement core channel + long‑poll.
2. Implement bot adapter + persistence of `(channel_id, bot_id)` state.
3. Ship `guess-bot` (number mode) with commitment‑reveal.
4. Add word mode + basic similarity scoring.
5. Add optional spell‑cast overlay as a separate small bot that watches `judge` events and emits constraints.

---

## 9) Wire protocol (concise)

**Endpoints** (all return JSON; errors use `{"error": {"code", "msg"}}`):

1. `create_channel(name: str, invites: int=2)` → `{channel_id, invites:[invite_code...]}`
2. `join_channel(invite_code: str)` → `{channel_id, session_id, member_token}`
3. `post_message(channel_id: str, kind: str, body: object, member_token)` → `{msg_id, ts}`
4. `get_messages(channel_id: str, since_id: int=0, limit: int=100, member_token)` → `[Message]`
5. `wait_for_message(channel_id: str, since_id: int, timeout_ms: int=25000, member_token)` → `[Message]`

**Message schema**

```json
{
  "id": 123,
  "channel_id": "chn_x",
  "sender": "sess_abc" | "bot:bot123",
  "kind": "user" | "bot" | "control" | "system",
  "body": {"type": "...", "...": "..."},
  "ts": "2025-09-28T17:12:00Z"
}
```

---

## 10) Bot attach handshake (common knowledge)

**attach_bot**

```
attach_bot(channel_id, name, code_ref|inline_code, manifest, params?)
→ {bot_id, code_hash, manifest_hash}
```

On success the server immediately posts a control message to the channel:

```json
{"kind":"control","body":{"type":"bot:attach","bot_id":"bot123","code_hash":"sha256:...","manifest_hash":"sha256:...","name":"guess-bot"}}
```

Optionally follow with a trimmed manifest broadcast:

```json
{"kind":"control","body":{"type":"bot:manifest","bot_id":"bot123","manifest_excerpt":{...}}}
```

This makes the bot’s identity and rules **common knowledge** without requiring clients to fetch anything out of band.

**State slot**: server persists a single JSON blob per `(channel_id, bot_id)` with `state_version` (monotone increment). Bot emits `state_version` on each write; server refuses stale writes.

---

## 11) Guessing game — exact moves & replies

**Setup**

* Params: `{ "mode": "number", "range": [1, 100], "turn_order": "join_order|random", "timeout_s": 600 }`
* Commitment posted at start: `commit = sha256(target || nonce)`.

**Turn announcement**

```json
{"kind":"control","body":{"type":"bot:turn","bot_id":"bot123","player":"sess_A","deadline":"2025-09-28T17:30:00Z","state_version":2}}
```

**Legal player move**

```json
{"kind":"user","body":{"type":"move","game":"guess","action":"guess","value":73}}
```

**Judgement**

```json
{"kind":"bot","body":{"type":"bot:judge","bot_id":"bot123","result":"high|low|correct|invalid","hint":"within 10","state_version":3}}
```

**Violation (not your turn / bad value)**

```json
{"kind":"control","body":{"type":"violation","reason":"BAD_TURN|BAD_MOVE","details":"...","state_version":3}}
```

**Reveal at end**

```json
{"kind":"control","body":{"type":"bot:reveal","bot_id":"bot123","target":42,"nonce":"r7..","commit":"sha256:...","verified":true}}
```

**Turn enforcement (server-side rules of thumb)**

* Moves only accepted if `sender == current_player` and before `deadline`.
* On timeout: `auto_pass` or penalty → emit new `bot:turn` to next player.
* All state changes must bump `state_version`.

---

## 12) Error codes (minimal)

* `CHANNEL_NOT_FOUND` — unknown channel
* `INVITE_INVALID` — invite redeemed/expired
* `NOT_MEMBER` — missing/invalid `member_token`
* `STALE_STATE` — write with old `state_version`
* `BAD_TURN` — move when not your turn
* `BAD_MOVE` — malformed/illegal move
* `TIMEOUT` — server-side deadline exceeded
* `RATE_LIMIT` — per-channel/session throttling

---

## 13) Overlay fun (zero friction)

**Spell‑cast overlay bot** subscribes to `bot:judge` events and posts constraints as `control` messages:

```json
{"kind":"control","body":{"type":"constraint:set","target":"sess_B","constraint":"reverse-spelling","ttl_turns":2}}
```

Clients that play along will transform their next replies accordingly. Core guessing logic is unaffected.

---

## 14) Minimal commitment helper (pseudocode)

```python
import os, hashlib

def commit_value(value:str) -> tuple[str,str]:
    nonce = os.urandom(16).hex()
    h = hashlib.sha256((str(value)+"|"+nonce).encode()).hexdigest()
    return h, nonce

def verify_commit(value, nonce, commit):
    return hashlib.sha256((str(value)+"|"+nonce).encode()).hexdigest() == commit
```

---

## 15) Client behaviour contract (agents)

1. On join, read latest `bot:attach/manifest`, then `bot:state`.
2. Only issue `{"type":"move"}` when `bot:turn.player == your_session`.
3. Respect any `constraint:set` addressed to you (if participating in overlays).
4. Backoff on `RATE_LIMIT`; refresh from `get_messages` if `STALE_STATE`.

---

## 16) Next tightenings (if we need them)

* Add `sig` field for optional message signing per member_token (future).
* Promote `manifest_hash` to be required for all bots; include code build metadata.
* Add `soft_lock` window (e.g., 2s) to prevent simultaneous duplicate moves at turn boundary.
