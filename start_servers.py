#!/usr/bin/env python3
"""
Start both MCP server and OAuth proxy
"""

import subprocess
import sys
import time
import signal
import os

def signal_handler(sig, frame):
    print("\nShutting down services...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    print("Starting MCP Multiplayer services...")

    mcp_host = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port = os.getenv("MCP_PORT", "8201")
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "8100")

    # Start MCP server in background
    mcp_process = subprocess.Popen([
        sys.executable, "multiplayer_server.py"
    ])

    # Give MCP server time to start
    time.sleep(2)

    print("\n" + "="*50)
    print("MCP Multiplayer is running!")
    print("="*50)
    print(f"MCP Server:    http://{mcp_host}:{mcp_port}")
    print(f"OAuth Proxy:   http://{proxy_host}:{proxy_port}")
    print("="*50)

    # Start OAuth proxy in foreground
    try:
        oauth_process = subprocess.Popen([
            sys.executable, "oauth_proxy.py"
        ])
        oauth_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up processes
        mcp_process.terminate()
        mcp_process.wait()

if __name__ == "__main__":
    main()