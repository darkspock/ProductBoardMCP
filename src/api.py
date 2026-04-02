"""Thin async HTTP client for Productboard API v1 with retry on 429.

In HTTP mode, the user's token is read from the Authorization header
of each incoming MCP request (proxy mode). In stdio mode, it falls
back to the PRODUCTBOARD_API_TOKEN env var.
"""

from typing import Any
from contextvars import ContextVar

import asyncio
import os
import httpx

API_BASE = os.getenv("PRODUCTBOARD_API_BASE_URL", "https://api.productboard.com")
MAX_RETRIES = 3

# Per-request token set by middleware, falls back to env var
_request_token: ContextVar[str] = ContextVar("_request_token", default="")


def get_token() -> str:
    """Get the Productboard token for the current request."""
    return _request_token.get() or os.getenv("PRODUCTBOARD_API_TOKEN", "")


def set_token(token: str) -> None:
    """Set the Productboard token for the current request context."""
    _request_token.set(token)


class ProductboardAPIError(Exception):
    """Raised when the Productboard API returns an error."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(f"Productboard API error ({status_code}): {detail}")


def _raise_on_error(r: httpx.Response) -> None:
    if r.is_success:
        return
    try:
        body = r.json()
        errors = body.get("errors", [])
        detail = "; ".join(e.get("detail", e.get("title", "Unknown error")) for e in errors) if errors else r.text
    except Exception:
        detail = r.text
    raise ProductboardAPIError(r.status_code, detail)


async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Execute request with per-request token and retry on 429."""
    token = get_token()
    if not token:
        raise ProductboardAPIError(401, "No Productboard API token provided. Set Authorization header or PRODUCTBOARD_API_TOKEN env var.")

    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Version": "1",
        },
        timeout=30.0,
    ) as client:
        r: httpx.Response | None = None
        for attempt in range(MAX_RETRIES):
            call = getattr(client, method)
            r = await call(path, **kwargs)
            if r.status_code != 429:
                return r
            retry_after = int(r.headers.get("Retry-After", str(2 ** attempt)))
            await asyncio.sleep(retry_after)
        assert r is not None
        return r


async def get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    r = await _request("get", path, params=params)
    _raise_on_error(r)
    result: dict[str, Any] = r.json()
    return result


async def post(path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
    r = await _request("post", path, json=json)
    _raise_on_error(r)
    if not r.content:
        return {}
    result: dict[str, Any] = r.json()
    return result


async def patch(path: str, json: dict[str, Any]) -> dict[str, Any]:
    r = await _request("patch", path, json=json)
    _raise_on_error(r)
    result: dict[str, Any] = r.json()
    return result


async def put(path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
    r = await _request("put", path, json=json)
    _raise_on_error(r)
    result: dict[str, Any] = r.json()
    return result


async def delete(path: str) -> None:
    r = await _request("delete", path)
    _raise_on_error(r)
