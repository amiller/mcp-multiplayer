#!/usr/bin/env python3
"""
Test bot sandboxing - verifies RestrictedPython blocks dangerous operations
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from mcp_client import MCPClient
from config import print_config

def test_sandbox_restrictions():
    """Test that sandbox correctly blocks restricted operations"""
    print_config()
    print("\nTesting bot sandboxing...")
    print("=" * 60)

    try:
        client = MCPClient().connect()
        print("✅ Connected")

        with open("tests/fixtures/RestrictedBots.py") as f:
            bot_code = f.read()

        # Test 1: SandboxProbeBot should be blocked (uses os/subprocess)
        print("\n🔍 Test 1: SandboxProbeBot (should block os/subprocess imports)")
        create_resp = client.call_tool("create_channel", {
            "name": "Sandbox Test",
            "slots": ["bot:probe", "invite:admin"],
            "bot_code": bot_code.split("# EvalShellBot")[0]  # Just the probe bot
        })

        if "Import of 'os' is not allowed" in str(create_resp):
            print("✅ Correctly blocked os import")
        else:
            print("❌ Failed to block os import")

        # Test 2: EvalShellBot should be blocked (uses eval/exec/__builtins__)
        print("\n🔍 Test 2: EvalShellBot (should block eval/exec/__builtins__)")
        eval_bot = """
import sys, io, traceback

class EvalShellBot:
    def __init__(self, ctx, params):
        self.ctx = ctx
        self.params = params
        self.globals = {"ctx": ctx, "__builtins__": __builtins__}

    def on_init(self):
        self.ctx.post("bot", {"type": "ready", "message": "Ready"})

    def on_message(self, msg):
        code = msg.get("body", {}).get("text", "")
        if code.startswith(">"):
            result = eval(code[1:], self.globals)
            self.ctx.post("bot", {"result": result})
"""
        create_resp = client.call_tool("create_channel", {
            "name": "Eval Test",
            "slots": ["bot:eval", "invite:admin"],
            "bot_code": eval_bot
        })

        response_str = str(create_resp)
        if "__builtins__" in response_str and "invalid variable name" in response_str:
            print("✅ Correctly blocked __builtins__")
        if "Eval calls are not allowed" in response_str:
            print("✅ Correctly blocked eval()")

        if "__builtins__" not in response_str or "Eval" not in response_str:
            print("❌ Failed to block eval/builtins")

        # Test 3: Valid bot should work (uses only allowed imports)
        print("\n🔍 Test 3: ValidBot (should work with allowed imports)")
        valid_bot = """
import random
import json

class ValidBot:
    def __init__(self, ctx, params):
        self.ctx = ctx

    def on_init(self):
        self.ctx.post("bot", {"type": "ready", "number": random.randint(1, 100)})

    def on_message(self, msg):
        if msg.get("kind") == "user":
            data = json.dumps({"echo": msg.get("body")})
            self.ctx.post("bot", {"data": data})
"""
        create_resp = client.call_tool("create_channel", {
            "name": "Valid Test",
            "slots": ["bot:valid", "invite:admin"],
            "bot_code": valid_bot
        })

        if "channel_id" in str(create_resp):
            print("✅ Valid bot created successfully")
        else:
            print("❌ Valid bot failed to create")

        print("\n" + "=" * 60)
        print("✅ Sandbox test complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(test_sandbox_restrictions())
