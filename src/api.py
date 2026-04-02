"""Thin async HTTP client for Productboard API v2."""

import os
import httpx

API_BASE = os.getenv("PRODUCTBOARD_API_BASE_URL", "https://api.productboard.com/v2")
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


async def get(path: str, params: dict | None = None) -> dict:
    r = await _get_client().get(path, params=params)
    r.raise_for_status()
    return r.json()


async def post(path: str, json: dict) -> dict:
    r = await _get_client().post(path, json=json)
    r.raise_for_status()
    return r.json()


async def patch(path: str, json: dict) -> dict:
    r = await _get_client().patch(path, json=json)
    r.raise_for_status()
    return r.json()


async def delete(path: str) -> None:
    r = await _get_client().delete(path)
    r.raise_for_status()
