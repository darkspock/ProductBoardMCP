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
