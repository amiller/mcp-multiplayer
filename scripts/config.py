#!/usr/bin/env python3
"""
Shared configuration for MCP scripts
"""

import os
from dotenv import load_dotenv

# Load script-specific environment variables
load_dotenv('.env.scripts')

# Configuration
BASE_URL = os.getenv('MCP_BASE_URL', 'http://127.0.0.1:8100')
CLIENT_NAME = os.getenv('MCP_CLIENT_NAME', 'MCP Script Client')
VERIFY_SSL = os.getenv('MCP_VERIFY_SSL', 'false').lower() == 'true'
TOKEN_FILE = os.getenv('MCP_TOKEN_FILE', 'mcp_tokens.json')

def get_base_url():
    """Get the base URL for MCP requests"""
    return BASE_URL

def get_client_name():
    """Get the client name for OAuth registration"""
    return CLIENT_NAME

def should_verify_ssl():
    """Whether to verify SSL certificates"""
    return VERIFY_SSL

def get_token_file():
    """Get the token file path"""
    return TOKEN_FILE

def print_config():
    """Print current configuration"""
    print(f"MCP Base URL: {BASE_URL}")
    print(f"Client Name: {CLIENT_NAME}")
    print(f"Verify SSL: {VERIFY_SSL}")
    print(f"Token File: {TOKEN_FILE}")