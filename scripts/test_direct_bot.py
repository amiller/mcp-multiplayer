#!/usr/bin/env python3
"""
Test bot directly by calling channel_manager without MCP
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from channel_manager import ChannelManager
from bot_manager import BotManager, BotDefinition

def test_direct_bot():
    print("Testing bot logic directly...")

    cm = ChannelManager()
    bm = BotManager(cm)

    # Attach bot manager to channel manager
    cm.bot_manager = bm

    # Create channel with bot
    result = cm.create_channel(
        name="Direct Bot Test",
        slots=["bot:guess-referee", "invite:player1", "invite:player2"],
        bots=[{
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
    )

    channel_id = result["channel_id"]
    invites = result["invites"]
    print(f"✅ Created channel: {channel_id}")

    # Manually attach bot (the MCP server does this automatically)
    from bot_manager import BotDefinition
    bot_def = BotDefinition(
        name="GuessBot",
        version="1.0",
        code_ref="builtin://GuessBot",
        manifest={
            "summary": "Turn-based number guessing referee",
            "hooks": ["on_init", "on_join", "on_message"],
            "emits": ["prompt", "state", "turn", "judge"],
            "params": {"mode": "number", "range": [1, 100]}
        }
    )
    attach_result = bm.attach_bot(channel_id, bot_def)
    print(f"✅ Bot attached: {attach_result['bot_id']}")

    # Join players
    alice_join = cm.join_channel(invites[0], "alice_session")
    bm.dispatch_join(alice_join["channel_id"], "alice_session")  # Notify bots
    bob_join = cm.join_channel(invites[1], "bob_session")
    bm.dispatch_join(bob_join["channel_id"], "bob_session")  # Notify bots
    print(f"✅ Alice joined as: {alice_join['slot_id']}")
    print(f"✅ Bob joined as: {bob_join['slot_id']}")

    # Check initial messages
    sync1 = cm.sync_messages(channel_id, "alice_session")
    print(f"📥 Initial messages: {len(sync1['messages'])}")

    for i, msg in enumerate(sync1['messages']):
        body = msg.get('body', {})
        sender = msg.get('sender', 'unknown')[:15]
        print(f"   {i+1}. {sender}: {body}")

    # Bob makes a guess (it's his turn according to message 10)
    print("\n🎯 Bob makes guess with proper structure...")
    guess_body = {
        "type": "move",
        "game": "guess",
        "action": "guess",
        "value": 50
    }
    bob_msg = cm.post_message(channel_id, "bob_session", "user", guess_body)
    print(f"✅ Message posted: {bob_msg['msg_id']}")

    # Notify bots about the message (like MCP server does)
    message = {
        "id": bob_msg["msg_id"],
        "channel_id": channel_id,
        "sender": "bob_session",
        "kind": "user",
        "body": guess_body,
        "ts": bob_msg["ts"]
    }
    bm.dispatch_message(channel_id, message)

    # Check for bot response
    sync2 = cm.sync_messages(channel_id, "alice_session")
    new_messages = sync2['messages'][len(sync1['messages']):]
    print(f"📥 New messages after guess: {len(new_messages)}")

    for msg in new_messages:
        sender = msg.get('sender', 'unknown')[:15]
        body = msg.get('body', {})
        print(f"   📨 {sender}: {body}")

    return len(new_messages) > 1  # Should have Alice's message + bot response

if __name__ == "__main__":
    success = test_direct_bot()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Bot response test")