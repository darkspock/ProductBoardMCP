# Productboard MCP Server

A lightweight [MCP](https://modelcontextprotocol.io) server that gives Claude (and any MCP client) access to the Productboard API. Built with [FastMCP](https://github.com/jlowin/fastmcp).

## Features

18 tools covering the full Productboard API v2:

| Category | Tools |
|----------|-------|
| **Features** | `list_features`, `get_feature`, `create_feature`, `update_feature`, `delete_feature` |
| **Products** | `list_products`, `create_product`, `product_hierarchy` |
| **Notes** | `create_note`, `list_notes` |
| **Objectives** | `list_objectives`, `create_objective`, `update_objective` |
| **Releases** | `list_releases`, `create_release`, `update_release`, `release_timeline`, `release_status_update` |

## Why a Rewrite?

This project exists because the original [Enreign/productboard-mcp](https://github.com/Enreign/productboard-mcp) — while a solid proof of concept — has several issues that make it hard to adopt, deploy, and maintain:

- **Heavily over-engineered for what it does.** 55 TypeScript files and 5,000+ lines of code to wrap 18 simple REST calls. Custom ToolRegistry, ProtocolHandler, Validator, CacheModule, RateLimiter, permission discovery system, multi-layer error hierarchy — all for endpoints that are essentially `GET /entities?type[]=feature`. The abstraction layers are deeper than the actual business logic.

- **Dead code.** Three key result tools (`pb_keyresult_list`, `pb_keyresult_create`, `pb_keyresult_update`) return early with a hardcoded "not supported" message. The code after the early return is unreachable but ships anyway.

- **stdio only — no remote transport.** The original only supports `StdioServerTransport`, which means every user must clone the repo, install Node.js dependencies, and configure their own API token locally. There's no HTTP transport for team-wide deployment as a Claude custom connector.

- **Build issues.** The project doesn't compile cleanly with its own SDK version (`@modelcontextprotocol/sdk@1.27.1`) due to type mismatches in the `CallToolRequestSchema` handler. The build relies on `skipLibCheck: true` and a post-build `fix-imports.js` script to patch module paths.

- **Not an official SDK.** Despite the name and packaging, this is not affiliated with Productboard. It's a community project. Since all it does is call a public REST API, there's no reason to inherit its complexity.

This rewrite keeps the same 18 functional tools and the same Productboard API patterns, but delivers them in ~570 lines of Python across 4 files, with stdio and HTTP transport working out of the box.

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- A Productboard API token (Settings > Integrations in Productboard)

### Install

```bash
git clone https://github.com/darkspock/ProductBoardMCP.git
cd ProductBoardMCP
uv sync
```

### Run (stdio — local use with Claude Desktop)

```bash
PRODUCTBOARD_API_TOKEN=your-token uv run python -m src
```

Or create a `.env` file:

```env
PRODUCTBOARD_API_TOKEN=your-token
```

```bash
uv run python -m src
```

### Run (HTTP — remote deployment for Claude custom connectors)

```bash
MCP_TRANSPORT=httpStream PORT=3000 uv run python -m src
```

The server will listen on `http://0.0.0.0:3000/mcp`.

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "productboard": {
      "command": "uv",
      "args": ["run", "python", "-m", "src"],
      "cwd": "/path/to/ProductBoardMCP",
      "env": {
        "PRODUCTBOARD_API_TOKEN": "your-token"
      }
    }
  }
}
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PRODUCTBOARD_API_TOKEN` | Yes | — | Bearer token from Productboard |
| `MCP_TRANSPORT` | No | `stdio` | `stdio` or `httpStream` |
| `PORT` | No | `3000` | HTTP port (only in httpStream mode) |
| `PRODUCTBOARD_API_BASE_URL` | No | `https://api.productboard.com/v2` | API base URL |

## Deploying as a Claude Custom Connector

1. Deploy with `MCP_TRANSPORT=httpStream` to any HTTPS host (Railway, Render, Fly.io, AWS, etc.)
2. In Claude, go to **Organization Settings > Connectors**
3. Click **"Add custom connector"**
4. Enter the server URL (e.g., `https://your-host.com/mcp`)
5. Click **"Add"**

Team members can then connect via **Settings > Connectors > Productboard > Connect**.

## Acknowledgments

This project is a Python/FastMCP rewrite of [Enreign/productboard-mcp](https://github.com/Enreign/productboard-mcp) by [Stanislav Shymanskyi](https://github.com/Enreign). The original TypeScript implementation (MIT License, v0.2.1) provided the foundation for all tool definitions and Productboard API integration patterns used here. Thank you for the excellent work!

## License

[MIT](LICENSE)
