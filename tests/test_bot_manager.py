#!/usr/bin/env python3
"""
Tests for Bot Manager
"""

import pytest
from unittest.mock import Mock, patch
from channel_manager import ChannelManager
from bot_manager import BotManager, BotDefinition, BotContext

class TestBotManager:
    def test_initialization(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        assert bm.channel_manager == cm
        assert isinstance(bm.bot_instances, dict)
        assert isinstance(bm.bot_classes, dict)

    def test_load_builtin_bots(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Should load GuessBot from bots/guess_bot.py
        assert "GuessBot" in bm.bot_classes

    def test_attach_bot_with_builtin(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Create a channel
        result = cm.create_channel("Test", ["invite:player1", "invite:player2"])
        channel_id = result["channel_id"]

        # Define bot
        bot_def = BotDefinition(
            name="GuessBot",
            version="1.0",
            code_ref="builtin://GuessBot",
            manifest={
                "summary": "Guessing game referee",
                "hooks": ["on_init", "on_join", "on_message"],
                "emits": ["prompt", "state", "turn", "judge"],
                "params": {"mode": "number", "range": [1, 100]}
            }
        )

        # Attach bot
        attach_result = bm.attach_bot(channel_id, bot_def)

        assert "bot_id" in attach_result
        assert "code_hash" in attach_result
        assert "manifest_hash" in attach_result

        # Check bot instance was created
        assert channel_id in bm.bot_instances
        bot_id = attach_result["bot_id"]
        assert bot_id in bm.bot_instances[channel_id]

        # Check system messages were posted
        channel = cm.channels[channel_id]
        system_messages = [m for m in channel["messages"] if m.kind == "system"]
        assert len(system_messages) >= 2  # bot:attach + bot:manifest

    def test_attach_bot_with_inline_code(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Create a channel
        result = cm.create_channel("Test", ["invite:player1"])
        channel_id = result["channel_id"]

        # Define bot with inline code
        inline_code = '''
class SimpleBot:
    def __init__(self, ctx, params):
        self.ctx = ctx
        self.params = params

    def on_init(self):
        self.ctx.post("bot", {"type": "hello", "message": "Bot initialized"})
'''

        bot_def = BotDefinition(
            name="SimpleBot",
            version="1.0",
            inline_code=inline_code,
            manifest={
                "summary": "Simple test bot",
                "hooks": ["on_init"]
            }
        )

        # Attach bot
        attach_result = bm.attach_bot(channel_id, bot_def)

        assert "bot_id" in attach_result
        bot_id = attach_result["bot_id"]

        # Check bot instance was created
        assert channel_id in bm.bot_instances
        assert bot_id in bm.bot_instances[channel_id]

    def test_attach_bot_invalid_channel(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        bot_def = BotDefinition(
            name="TestBot",
            version="1.0",
            code_ref="builtin://GuessBot"
        )

        with pytest.raises(ValueError, match="CHANNEL_NOT_FOUND"):
            bm.attach_bot("invalid_channel", bot_def)

    def test_attach_bot_unknown_builtin(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        result = cm.create_channel("Test", ["invite:player1"])
        channel_id = result["channel_id"]

        bot_def = BotDefinition(
            name="UnknownBot",
            version="1.0",
            code_ref="builtin://UnknownBot"
        )

        with pytest.raises(ValueError, match="Unknown builtin bot"):
            bm.attach_bot(channel_id, bot_def)

    def test_dispatch_message(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Create channel and attach bot
        result = cm.create_channel("Test", ["invite:player1"])
        channel_id = result["channel_id"]

        bot_def = BotDefinition(
            name="GuessBot",
            version="1.0",
            code_ref="builtin://GuessBot",
            manifest={"hooks": ["on_message"]}
        )

        attach_result = bm.attach_bot(channel_id, bot_def)
        bot_id = attach_result["bot_id"]

        # Mock the bot hook call
        with patch.object(bm, '_call_bot_hook') as mock_hook:
            test_message = {"kind": "user", "body": {"type": "test"}}
            bm.dispatch_message(channel_id, test_message)

            mock_hook.assert_called_once_with(channel_id, bot_id, "on_message", test_message)

    def test_dispatch_join(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Create channel and attach bot
        result = cm.create_channel("Test", ["invite:player1"])
        channel_id = result["channel_id"]

        bot_def = BotDefinition(
            name="GuessBot",
            version="1.0",
            code_ref="builtin://GuessBot",
            manifest={"hooks": ["on_join"]}
        )

        attach_result = bm.attach_bot(channel_id, bot_def)
        bot_id = attach_result["bot_id"]

        # Mock the bot hook call
        with patch.object(bm, '_call_bot_hook') as mock_hook:
            bm.dispatch_join(channel_id, "sess_123")

            mock_hook.assert_called_once_with(channel_id, bot_id, "on_join", "sess_123")

    def test_bot_state_management(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Create channel and attach bot
        result = cm.create_channel("Test", ["invite:player1"])
        channel_id = result["channel_id"]

        bot_def = BotDefinition(
            name="GuessBot",
            version="1.0",
            code_ref="builtin://GuessBot"
        )

        attach_result = bm.attach_bot(channel_id, bot_def)
        bot_id = attach_result["bot_id"]

        # Test state operations - GuessBot initializes state on creation
        initial_state = bm.get_bot_state(channel_id, bot_id)
        assert isinstance(initial_state, dict)  # Should have state after initialization

        test_state = {"key": "value", "count": 42}
        bm.set_bot_state(channel_id, bot_id, test_state)

        retrieved_state = bm.get_bot_state(channel_id, bot_id)
        assert retrieved_state == test_state

        # State version should increment (starts at 1 from GuessBot init, then +1 from our set)
        version = bm.get_bot_state_version(channel_id, bot_id)
        assert version == 2

    def test_post_message_from_bot(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Create channel and attach bot
        result = cm.create_channel("Test", ["invite:player1"])
        channel_id = result["channel_id"]

        bot_def = BotDefinition(
            name="GuessBot",
            version="1.0",
            code_ref="builtin://GuessBot"
        )

        attach_result = bm.attach_bot(channel_id, bot_def)
        bot_id = attach_result["bot_id"]

        # Post message from bot
        body = {"type": "test", "message": "hello"}
        post_result = bm.post_message_from_bot(channel_id, bot_id, "bot", body)

        assert "msg_id" in post_result
        assert "ts" in post_result

        # Check message was stored
        messages = cm.channels[channel_id]["messages"]
        bot_messages = [m for m in messages if m.sender == f"bot:{bot_id}"]
        assert len(bot_messages) >= 1

        # Message should have bot metadata
        last_bot_msg = bot_messages[-1]
        assert last_bot_msg.body["bot_id"] == bot_id
        assert "state_version" in last_bot_msg.body

    def test_get_channel_bots(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Create channel
        result = cm.create_channel("Test", ["invite:player1"])
        channel_id = result["channel_id"]

        # No bots initially
        bots = bm.get_channel_bots(channel_id)
        assert bots == []

        # Attach a bot
        bot_def = BotDefinition(
            name="GuessBot",
            version="1.0",
            code_ref="builtin://GuessBot",
            manifest={"summary": "Test bot"}
        )

        attach_result = bm.attach_bot(channel_id, bot_def)
        bot_id = attach_result["bot_id"]

        # Should have one bot
        bots = bm.get_channel_bots(channel_id)
        assert len(bots) == 1
        assert bots[0]["bot_id"] == bot_id
        assert bots[0]["name"] == "GuessBot"
        assert bots[0]["version"] == "1.0"

class TestBotContext:
    def test_bot_context_creation(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        ctx = BotContext("test_channel", "test_bot", bm)

        assert ctx.channel_id == "test_channel"
        assert ctx.bot_id == "test_bot"
        assert ctx.bot_manager == bm
        assert ctx.env == {}

    def test_bot_context_post(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        # Create channel
        result = cm.create_channel("Test", ["invite:player1"])
        channel_id = result["channel_id"]

        ctx = BotContext(channel_id, "test_bot", bm)

        # Mock the bot manager's post method
        with patch.object(bm, 'post_message_from_bot') as mock_post:
            mock_post.return_value = {"msg_id": 1, "ts": "2025-01-01T00:00:00Z"}

            result = ctx.post("bot", {"type": "test"})

            mock_post.assert_called_once_with(
                channel_id, "test_bot", "bot", {"type": "test"}
            )

    def test_bot_context_state(self):
        cm = ChannelManager()
        bm = BotManager(cm)

        ctx = BotContext("test_channel", "test_bot", bm)

        # Mock state methods
        with patch.object(bm, 'get_bot_state') as mock_get, \
             patch.object(bm, 'set_bot_state') as mock_set:

            mock_get.return_value = {"key": "value"}

            # Test get_state
            state = ctx.get_state()
            mock_get.assert_called_once_with("test_channel", "test_bot")

            # Test set_state
            new_state = {"new": "state"}
            ctx.set_state(new_state)
            mock_set.assert_called_once_with("test_channel", "test_bot", new_state)