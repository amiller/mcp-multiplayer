# Dstack deployment

Deploy MCP Multiplayer to Phala's dstack TEE platform with OAuth 2.1 authentication.

## Architecture
```
External HTTPS → dstack-gateway → OAuth Proxy (port 8100) → MCP Server (port 8201)
```

## Key configuration

Environment variables:
- `USE_SSL=false` - dstack-gateway handles HTTPS termination
- `PROXY_HOST=0.0.0.0` - bind to all interfaces in container
- `MCP_HOST=127.0.0.1` - internal MCP server binding
- `PROXY_PORT=8100` - OAuth proxy port
- `MCP_PORT=8201` - MCP server port

Files:
- `docker-compose.yml` - development with local build
- `docker-compose-deploy.yml` - production with SHA256-pinned image
- `start_servers.py` - service orchestrator

## Deployment

Build and push image:
```bash
docker build -t mcp-multiplayer .
docker tag mcp-multiplayer YOUR_REGISTRY/mcp-multiplayer
docker push YOUR_REGISTRY/mcp-multiplayer
docker images --digests YOUR_REGISTRY/mcp-multiplayer
```

Update `docker-compose-deploy.yml` with registry and SHA256 hash, then deploy:
```bash
phala deploy docker-compose-deploy.yml --node 3
```

Verify deployment:
```bash
curl https://YOUR_URL/.well-known/oauth-authorization-server
```

## Notes

- Only port 8100 (OAuth proxy) exposed externally
- MCP server runs on port 8201 internally
- Dstack provides HTTPS termination, no SSL certificates needed inside container
- Based on successful deployment pattern from ambient_mcp project