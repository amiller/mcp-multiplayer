#!/usr/bin/env python3
"""
Tests for cursor watermark semantics in sync_messages
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from channel_manager import ChannelManager

class TestCursorWatermark:
    def test_cursor_starts_at_zero(self):
        cm = ChannelManager()
        result = cm.create_channel(name="Test", slots=["invite:p1"])
        channel_id = result["channel_id"]
        invite = result["invites"][0]
        cm.join_channel(invite, "sess_1")

        # First sync with no cursor
        sync = cm.sync_messages(channel_id, "sess_1", cursor=None)

        # Should return cursor (may be 0 if no messages)
        assert "cursor" in sync
        assert sync["cursor"] >= 0

    def test_cursor_only_advances_with_new_messages(self):
        cm = ChannelManager()
        result = cm.create_channel(name="Test", slots=["invite:p1"])
        channel_id = result["channel_id"]
        invite = result["invites"][0]
        cm.join_channel(invite, "sess_1")

        # Get initial state
        sync1 = cm.sync_messages(channel_id, "sess_1")
        cursor1 = sync1["cursor"]

        # Poll again with same cursor - no new messages
        sync2 = cm.sync_messages(channel_id, "sess_1", cursor=cursor1)
        cursor2 = sync2["cursor"]

        # Cursor should NOT advance
        assert cursor2 == cursor1
        assert len(sync2["messages"]) == 0

    def test_cursor_advances_to_newest_message(self):
        cm = ChannelManager()
        result = cm.create_channel(name="Test", slots=["invite:p1"])
        channel_id = result["channel_id"]
        invite = result["invites"][0]
        cm.join_channel(invite, "sess_1")

        # Get initial cursor
        sync1 = cm.sync_messages(channel_id, "sess_1")
        cursor1 = sync1["cursor"]

        # Post 3 new messages
        cm.post_message(channel_id, "sess_1", "user", {"msg": "1"})
        cm.post_message(channel_id, "sess_1", "user", {"msg": "2"})
        result3 = cm.post_message(channel_id, "sess_1", "user", {"msg": "3"})
        msg3_id = result3["msg_id"]

        # Sync with old cursor
        sync2 = cm.sync_messages(channel_id, "sess_1", cursor=cursor1)
        cursor2 = sync2["cursor"]

        # Should get all 3 messages and cursor at highest
        assert len(sync2["messages"]) == 3
        assert cursor2 == msg3_id

    def test_cursor_never_goes_backwards(self):
        cm = ChannelManager()
        result = cm.create_channel(name="Test", slots=["invite:p1"])
        channel_id = result["channel_id"]
        invite = result["invites"][0]
        cm.join_channel(invite, "sess_1")

        # Get initial state
        sync1 = cm.sync_messages(channel_id, "sess_1")
        cursor1 = sync1["cursor"]

        # Post message
        cm.post_message(channel_id, "sess_1", "user", {"msg": "new"})

        # Sync to advance cursor
        sync2 = cm.sync_messages(channel_id, "sess_1", cursor=cursor1)
        cursor2 = sync2["cursor"]
        assert cursor2 > cursor1

        # Poll again - cursor should stay at cursor2
        sync3 = cm.sync_messages(channel_id, "sess_1", cursor=cursor2)
        cursor3 = sync3["cursor"]
        assert cursor3 == cursor2

    def test_repeated_polling_stays_stable(self):
        cm = ChannelManager()
        result = cm.create_channel(name="Test", slots=["invite:p1"])
        channel_id = result["channel_id"]
        invite = result["invites"][0]
        cm.join_channel(invite, "sess_1")

        # Get cursor
        sync1 = cm.sync_messages(channel_id, "sess_1")
        cursor = sync1["cursor"]

        # Poll 10 times with same cursor
        for _ in range(10):
            sync = cm.sync_messages(channel_id, "sess_1", cursor=cursor)
            assert sync["cursor"] == cursor  # Should never change
            assert len(sync["messages"]) == 0

    def test_cursor_with_multiple_clients(self):
        cm = ChannelManager()
        result = cm.create_channel(name="Test", slots=["invite:p1", "invite:p2"])
        channel_id = result["channel_id"]

        cm.join_channel(result["invites"][0], "sess_1")
        cm.join_channel(result["invites"][1], "sess_2")

        # Both clients get initial state
        sync1 = cm.sync_messages(channel_id, "sess_1")
        sync2 = cm.sync_messages(channel_id, "sess_2")
        cursor1 = sync1["cursor"]
        cursor2 = sync2["cursor"]

        # Cursors should be equal (same messages)
        assert cursor1 == cursor2

        # sess_1 posts a message
        cm.post_message(channel_id, "sess_1", "user", {"msg": "hello"})

        # sess_2 syncs and gets the message
        sync2_new = cm.sync_messages(channel_id, "sess_2", cursor=cursor2)
        assert len(sync2_new["messages"]) == 1
        assert sync2_new["messages"][0]["body"]["msg"] == "hello"

        # sess_2's cursor advances
        assert sync2_new["cursor"] > cursor2

    def test_cursor_idempotent_when_no_new_messages(self):
        cm = ChannelManager()
        result = cm.create_channel(name="Test", slots=["invite:p1"])
        channel_id = result["channel_id"]
        invite = result["invites"][0]
        cm.join_channel(invite, "sess_1")

        # Post a message
        cm.post_message(channel_id, "sess_1", "user", {"msg": "test"})

        # Sync to get it
        sync1 = cm.sync_messages(channel_id, "sess_1")
        cursor1 = sync1["cursor"]

        # Sync again multiple times - should be identical
        for _ in range(5):
            sync = cm.sync_messages(channel_id, "sess_1", cursor=cursor1)
            assert sync["cursor"] == cursor1
            assert sync["messages"] == []
