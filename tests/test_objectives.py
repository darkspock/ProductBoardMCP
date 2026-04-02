"""Integration tests for objective and key result tools."""

import pytest
from tests.helpers import extract_created_id


async def test_objective_crud(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_objective", {
        "name": "pytest objective",
        "description": "test",
    })
    assert "created" in result.content[0].text.lower()
    oid = extract_created_id(result.content[0].text)

    try:
        result = await mcp.call_tool("get_objective", {"id": oid})
        assert "pytest objective" in result.content[0].text

        result = await mcp.call_tool("update_objective", {"id": oid, "name": "pytest obj UPDATED"})
        assert "updated" in result.content[0].text.lower()

        result = await mcp.call_tool("list_objectives", {})
        assert oid in result.content[0].text
    finally:
        result = await mcp.call_tool("delete_objective", {"id": oid})
        assert "deleted" in result.content[0].text.lower()


async def test_objective_links(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_objective", {
        "name": "pytest obj links",
        "description": "test",
    })
    oid = extract_created_id(result.content[0].text)

    try:
        result = await mcp.call_tool("list_objective_features", {"objective_id": oid})
        text = result.content[0].text.lower()
        assert "no features" in text or "linked" in text

        result = await mcp.call_tool("list_objective_initiatives", {"objective_id": oid})
        text = result.content[0].text.lower()
        assert "no initiatives" in text or "linked" in text
    finally:
        await mcp.call_tool("delete_objective", {"id": oid})


async def test_key_result_crud(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_objective", {
        "name": "pytest kr parent",
        "description": "test",
    })
    oid = extract_created_id(result.content[0].text)

    result = await mcp.call_tool("create_key_result", {
        "name": "pytest kr",
        "parent_objective_id": oid,
        "target_value": 100,
    })
    text = result.content[0].text
    if text.startswith("Error:"):
        await mcp.call_tool("delete_objective", {"id": oid})
        pytest.skip("Key results not enabled on this workspace")

    kr_id = extract_created_id(text)
    try:
        result = await mcp.call_tool("get_key_result", {"id": kr_id})
        assert "pytest kr" in result.content[0].text

        result = await mcp.call_tool("update_key_result", {"id": kr_id, "current_value": 50})
        assert "updated" in result.content[0].text.lower()

        result = await mcp.call_tool("delete_key_result", {"id": kr_id})
        assert "deleted" in result.content[0].text.lower()
    except Exception:
        await mcp.call_tool("delete_key_result", {"id": kr_id})
        raise
    finally:
        await mcp.call_tool("delete_objective", {"id": oid})
