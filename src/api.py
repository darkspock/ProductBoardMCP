"""Thin async HTTP client for Productboard API v1."""

import os
import httpx

API_BASE = os.getenv("PRODUCTBOARD_API_BASE_URL", "https://api.productboard.com")
API_TOKEN = os.getenv("PRODUCTBOARD_API_TOKEN", "")

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

    def __init__(self, status_code: int, detail: str):
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


async def get(path: str, params: dict | None = None) -> dict:
    r = await _get_client().get(path, params=params)
    _raise_on_error(r)
    return r.json()


async def post(path: str, json: dict | None = None) -> dict:
    r = await _get_client().post(path, json=json)
    _raise_on_error(r)
    return r.json()


async def patch(path: str, json: dict) -> dict:
    r = await _get_client().patch(path, json=json)
    _raise_on_error(r)
    return r.json()


async def put(path: str, json: dict | None = None) -> dict:
    r = await _get_client().put(path, json=json)
    _raise_on_error(r)
    return r.json()


async def delete(path: str) -> None:
    r = await _get_client().delete(path)
    _raise_on_error(r)
