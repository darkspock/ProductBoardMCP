"""Integration tests for initiative tools.

Skips if initiatives are not enabled on the workspace plan.
"""

import pytest
from tests.helpers import extract_created_id


async def test_initiative_crud(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_initiative", {
        "name": "pytest initiative",
        "description": "test",
    })
    text = result.content[0].text
    if text.startswith("Error:"):
        pytest.skip("Initiatives not enabled on this workspace")

    assert "created" in text.lower()
    iid = extract_created_id(text)

    try:
        result = await mcp.call_tool("get_initiative", {"id": iid})
        assert "pytest initiative" in result.content[0].text

        result = await mcp.call_tool("update_initiative", {"id": iid, "name": "pytest init UPDATED"})
        assert "updated" in result.content[0].text.lower()

        result = await mcp.call_tool("list_initiatives", {})
        assert iid in result.content[0].text

        result = await mcp.call_tool("list_initiative_features", {"initiative_id": iid})
        text = result.content[0].text.lower()
        assert "no features" in text or "linked" in text

        result = await mcp.call_tool("list_initiative_objectives", {"initiative_id": iid})
        text = result.content[0].text.lower()
        assert "no objectives" in text or "linked" in text
    finally:
        result = await mcp.call_tool("delete_initiative", {"id": iid})
        assert "deleted" in result.content[0].text.lower()
