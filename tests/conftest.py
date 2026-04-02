"""Shared fixtures for integration tests.

These tests hit the real Productboard API. They require:
  - PRODUCTBOARD_API_TOKEN in .env or environment
  - A Productboard workspace (can be a trial/sandbox)

NOT intended for CI — run manually with: uv run pytest
"""

from __future__ import annotations

import os
import pytest
from dotenv import load_dotenv

load_dotenv()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: tests that hit the real Productboard API")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark all tests as integration and skip if no token."""
    token = os.getenv("PRODUCTBOARD_API_TOKEN", "")
    for item in items:
        item.add_marker(pytest.mark.integration)
        if not token:
            item.add_marker(pytest.mark.skip(reason="PRODUCTBOARD_API_TOKEN not set"))


@pytest.fixture()
def mcp():  # type: ignore[no-untyped-def]
    # Reset the httpx client for each test to avoid event loop issues
    from src import api
    api._client = None
    from src.server import mcp
    return mcp


@pytest.fixture()
async def product_id(mcp) -> str:  # type: ignore[no-untyped-def]
    """Get first product ID from workspace."""
    result = await mcp.call_tool("list_products", {})
    text = result.content[0].text
    for line in text.split("\n"):
        if "ID:" in line:
            raw = line.split("ID:")[1].strip()
            # Extract just the UUID (36 chars)
            return raw[:36]
    pytest.fail("No products found in workspace")
    return ""
