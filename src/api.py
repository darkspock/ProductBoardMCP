"""Thin async HTTP client for Productboard API v1 with retry on 429."""

from typing import Any

import asyncio
import os
import httpx

API_BASE = os.getenv("PRODUCTBOARD_API_BASE_URL", "https://api.productboard.com")
API_TOKEN = os.getenv("PRODUCTBOARD_API_TOKEN", "")
MAX_RETRIES = 3

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Type": "application/json",
                "X-Version": "1",
            },
            timeout=30.0,
        )
    return _client


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
    """Execute request with retry on 429 (rate limit)."""
    r: httpx.Response | None = None
    for attempt in range(MAX_RETRIES):
        client = _get_client()
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
