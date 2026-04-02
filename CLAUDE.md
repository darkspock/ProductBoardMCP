# CLAUDE.md

## Project

Productboard MCP server built with FastMCP (Python). Provides 65 tools for the official Productboard API v1.

## Commands

```bash
uv run python -m src                    # Run (stdio)
MCP_TRANSPORT=httpStream uv run python -m src  # Run (HTTP)
uv run pytest -v                        # Tests (needs real API token in .env)
uv run mypy src/ --strict               # Type check
uv run ruff check src/ tests/           # Lint
```

## Architecture

- `src/api.py` — HTTP client (httpx) with retry on 429
- `src/helpers.py` — strip_html, to_html, error handler decorator
- `src/server.py` — All 65 FastMCP tools organized by resource
- `src/__main__.py` — Entry point (stdio or HTTP based on MCP_TRANSPORT)
- `tests/` — Integration tests against real Productboard API (not for CI)

## API

Uses official Productboard API v1 (`api.productboard.com`) with `X-Version: 1` header. NOT the undocumented `/v2/entities` endpoint.

## Conventions

- Tools return plain text strings, not JSON
- Errors are caught by `@handle_api_errors` and returned as `"Error: ..."` strings
- All functions have strict mypy types
- Notes API uses flat body for POST, `{data: ...}` wrapper for PATCH
- Release creation requires `release_group_id`
- Custom field set requires `field_type` discriminator
