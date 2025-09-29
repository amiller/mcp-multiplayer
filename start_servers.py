#!/usr/bin/env python3
"""
Start both MCP server and OAuth proxy for testing
"""

import os
import subprocess
import time
import sys
from multiprocessing import Process

def start_mcp_server():
    """Start the MCP server"""
    print("Starting MCP server on port 9201...")
    os.system("python multiplayer_server.py")

def start_oauth_proxy():
    """Start the OAuth proxy"""
    print("Starting OAuth proxy on port 9200...")
    os.system("python oauth_proxy.py")

def main():
    """Start both servers"""
    print("Starting MCP Multiplayer services...")

    # Start MCP server in background
    mcp_process = Process(target=start_mcp_server)
    mcp_process.start()

    # Give MCP server time to start
    time.sleep(2)

    # Start OAuth proxy in background
    proxy_process = Process(target=start_oauth_proxy)
    proxy_process.start()

    print("\n" + "="*50)
    print("MCP Multiplayer is running!")
    print("="*50)
    print("MCP Server:    http://127.0.0.1:9201")
    print("OAuth Proxy:   http://127.0.0.1:9200")
    print("Health Check:  http://127.0.0.1:9200/health")
    print("Debug Info:    http://127.0.0.1:9200/debug/info")
    print("="*50)
    print("Press Ctrl+C to stop both servers")

    try:
        # Wait for processes
        mcp_process.join()
        proxy_process.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        mcp_process.terminate()
        proxy_process.terminate()
        mcp_process.join()
        proxy_process.join()
        print("Servers stopped.")

if __name__ == "__main__":
    main()