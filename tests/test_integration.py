#!/usr/bin/env python3
"""
Simple Integration Test
Tests the core functionality: two players create a game and exchange messages
"""

import pytest
from channel_manager import ChannelManager
from bot_manager import BotManager


def test_two_players_basic_game():
    """Test two players creating a game and exchanging messages"""
    cm = ChannelManager()
    bm = BotManager(cm)

    # Player 1 creates a game
    result = cm.create_channel("Test Game", ["invite:alice", "invite:bob"])
    channel_id = result["channel_id"]
    invites = result["invites"]

    # Players join
    alice_join = cm.join_channel(invites[0], "alice_session")
    bob_join = cm.join_channel(invites[1], "bob_session")

    assert alice_join["channel_id"] == channel_id
    assert bob_join["channel_id"] == channel_id
    assert alice_join["slot_id"] != bob_join["slot_id"]

    # Players exchange messages
    alice_msg = cm.post_message(channel_id, "alice_session", "user", {"text": "Hi Bob!"})
    bob_msg = cm.post_message(channel_id, "bob_session", "user", {"text": "Hey Alice!"})

    # Both can sync messages
    alice_sync = cm.sync_messages(channel_id, "alice_session")
    bob_sync = cm.sync_messages(channel_id, "bob_session")

    # Should see each other's messages
    alice_messages = alice_sync["messages"]
    bob_messages = bob_sync["messages"]

    assert len(alice_messages) >= 2  # At least their two messages
    assert len(bob_messages) >= 2

    # Find the actual user messages
    user_messages = [m for m in alice_messages if m["kind"] == "user"]
    assert len(user_messages) == 2

    # Check message content
    alice_msg_found = any(m["body"]["text"] == "Hi Bob!" for m in user_messages)
    bob_msg_found = any(m["body"]["text"] == "Hey Alice!" for m in user_messages)

    assert alice_msg_found, "Alice's message not found"
    assert bob_msg_found, "Bob's message not found"


def test_game_with_bot():
    """Test game with a bot that responds to messages"""
    cm = ChannelManager()
    bm = BotManager(cm)

    # Create channel with GuessBot
    result = cm.create_channel(
        "Guess Game",
        ["bot:referee", "invite:player1"],
        bots=[{
            "slot": "bot:referee",
            "name": "GuessBot",
            "version": "1.0"
        }]
    )

    channel_id = result["channel_id"]
    invite_code = result["invites"][0]

    # Attach the bot properly
    from bot_manager import BotDefinition
    bot_def = BotDefinition(
        name="GuessBot",
        version="1.0",
        code_ref="builtin://GuessBot",
        manifest={"hooks": ["on_init", "on_join", "on_message"]}
    )
    bm.attach_bot(channel_id, bot_def)

    # Player joins
    cm.join_channel(invite_code, "player_session")

    # Player makes a guess
    cm.post_message(channel_id, "player_session", "user", {
        "type": "move",
        "game": "guess",
        "action": "guess",
        "value": 42
    })

    # Sync messages to see bot response
    sync_result = cm.sync_messages(channel_id, "player_session")
    messages = sync_result["messages"]

    # Should have system messages from bot initialization and possibly a response
    assert len(messages) > 1
    assert any(m["kind"] == "system" for m in messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])