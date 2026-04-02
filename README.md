# Productboard MCP Server

A lightweight [MCP](https://modelcontextprotocol.io) server that gives Claude (and any MCP client) full access to the [Productboard API v1](https://developer.productboard.com). Built with [FastMCP](https://github.com/jlowin/fastmcp).

## Tools (65)

| Category | Tools | Count |
|----------|-------|-------|
| **Features** | `list_features`, `get_feature`, `create_feature`, `update_feature`, `delete_feature` | 5 |
| **Feature links** | `list_feature_objectives`, `link_feature_objective`, `unlink_feature_objective`, `list_feature_initiatives`, `link_feature_initiative`, `unlink_feature_initiative` | 6 |
| **Feature statuses** | `list_feature_statuses` | 1 |
| **Products** | `list_products`, `get_product`, `update_product` | 3 |
| **Components** | `list_components`, `get_component`, `create_component`, `update_component` | 4 |
| **Notes** | `list_notes`, `get_note`, `create_note`, `update_note`, `delete_note` | 5 |
| **Note links & tags** | `link_note_to_entity`, `list_note_links`, `add_note_tag`, `remove_note_tag`, `list_note_tags` | 5 |
| **Objectives** | `list_objectives`, `get_objective`, `create_objective`, `update_objective`, `delete_objective` | 5 |
| **Objective links** | `list_objective_features`, `list_objective_initiatives` | 2 |
| **Key Results** | `list_key_results`, `get_key_result`, `create_key_result`, `update_key_result`, `delete_key_result` | 5 |
| **Initiatives** | `list_initiatives`, `get_initiative`, `create_initiative`, `update_initiative`, `delete_initiative` | 5 |
| **Initiative links** | `list_initiative_features`, `list_initiative_objectives` | 2 |
| **Releases** | `list_releases`, `get_release`, `create_release`, `update_release`, `delete_release` | 5 |
| **Release Groups** | `list_release_groups`, `get_release_group`, `create_release_group`, `update_release_group`, `delete_release_group` | 5 |
| **Feature-Release Assignments** | `list_feature_release_assignments`, `assign_feature_to_release` | 2 |
| **Custom Fields** | `list_custom_fields`, `get_custom_field_value`, `set_custom_field_value` | 3 |
| **Companies** | `list_companies`, `get_company` | 2 |

## Why a Rewrite?

This project started from [Enreign/productboard-mcp](https://github.com/Enreign/productboard-mcp) — a solid proof of concept, but with issues that made it hard to adopt:

- **Over-engineered.** 55 TypeScript files / 5,000+ lines to wrap simple REST calls. Custom ToolRegistry, ProtocolHandler, Validator, CacheModule, RateLimiter, permission discovery — abstraction layers deeper than the business logic.
- **Undocumented internal API.** Used `/v2/entities?type[]=feature` — an endpoint that does not appear anywhere in Productboard's [official API documentation](https://developer.productboard.com). The generic `entities` pattern with `type[]` filters is typical of an internal backend API, likely discovered by reverse engineering. This API has no versioning guarantees, no changelog, and no deprecation policy — it can break without notice. The official public API uses dedicated endpoints (`/features`, `/objectives`, `/key-results`, etc.) with proper documentation, OpenAPI spec, and stability commitments.
- **Low coverage.** Only 18 tools covering a fraction of the API. No initiatives, key results, components, custom fields, companies, release groups, or entity linking — partly because the internal API didn't support them (key results were hardcoded as "not supported").
- **Dead code.** Three key result tools returned early with "not supported" — the code after was unreachable.
- **stdio only.** No HTTP transport for team-wide deployment.
- **Build issues.** Didn't compile cleanly with its own SDK version.

This rewrite uses the **official Productboard API v1**, covers **60 tools** (vs 18), and delivers it all in **~1,700 lines of Python across 4 files** with stdio and HTTP transport out of the box.

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

### Connect from Claude Code (remote server)

Add to your `.claude/settings.json` or project settings:

```json
{
  "mcpServers": {
    "productboard": {
      "url": "https://your-host.com/mcp",
      "headers": {
        "Authorization": "Bearer your-productboard-token"
      }
    }
  }
}
```

Each user sets their own Productboard API token. The server proxies it to the Productboard API — no tokens are stored server-side.

### Connect from Claude Desktop (remote server)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "productboard": {
      "url": "https://your-host.com/mcp",
      "headers": {
        "Authorization": "Bearer your-productboard-token"
      }
    }
  }
}
```

### Local mode (stdio)

If you prefer running locally instead of connecting to a remote server:

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
| `PRODUCTBOARD_API_BASE_URL` | No | `https://api.productboard.com` | API base URL |

## Deploying as a Claude Custom Connector

### With Docker

```bash
docker build -t productboard-mcp .
docker run -p 3000:3000 productboard-mcp
```

No API token needed on the server — each user passes their own token via the `Authorization` header from their Claude config.

### On any host

1. Deploy with `MCP_TRANSPORT=httpStream` to any HTTPS host (Railway, Render, Fly.io, AWS, etc.)
2. In Claude, go to **Organization Settings > Connectors**
3. Click **"Add custom connector"**
4. Enter the server URL (e.g., `https://your-host.com/mcp`)
5. Click **"Add"**

Team members can then connect via **Settings > Connectors > Productboard > Connect**.

## Plan Restrictions

Some Productboard features are only available on certain plans. If a tool accesses a feature not enabled on your workspace, it will return a clear error message instead of failing silently:

- **Initiatives** — may not be available on all plans. Tools will return `"Error: Productboard API error (500): An unknown error occurred"`.
- **Key Results** — may not be available on all plans. Tools will return `"Error: ... keyResult model was not found. It either doesn't exist or it is not enabled for your space."`.

All other tools (features, products, components, notes, objectives, releases, release groups, custom fields, companies) work on all plans.

## Acknowledgments

This project is inspired by [Enreign/productboard-mcp](https://github.com/Enreign/productboard-mcp) by [Stanislav Shymanskyi](https://github.com/Enreign). The original TypeScript implementation (MIT License, v0.2.1) demonstrated that an MCP server for Productboard was viable and provided the initial inspiration. Thank you for paving the way!

## License

[MIT](LICENSE)
