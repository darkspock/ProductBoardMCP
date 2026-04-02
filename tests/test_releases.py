"""Integration tests for release and release group tools."""

import pytest
from tests.helpers import extract_created_id


@pytest.fixture()
async def release_group_id(mcp):  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_release_group", {
        "name": "pytest rg",
        "description": "test",
    })
    rgid = extract_created_id(result.content[0].text)
    yield rgid
    await mcp.call_tool("delete_release_group", {"id": rgid})


async def test_release_group_crud(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_release_group", {
        "name": "pytest rg crud",
        "description": "test",
    })
    assert "created" in result.content[0].text.lower()
    rgid = extract_created_id(result.content[0].text)

    try:
        result = await mcp.call_tool("get_release_group", {"id": rgid})
        assert "pytest rg crud" in result.content[0].text

        result = await mcp.call_tool("update_release_group", {"id": rgid, "name": "pytest rg UPDATED"})
        assert "updated" in result.content[0].text.lower()

        result = await mcp.call_tool("list_release_groups", {})
        assert rgid in result.content[0].text
    finally:
        result = await mcp.call_tool("delete_release_group", {"id": rgid})
        assert "deleted" in result.content[0].text.lower()


async def test_release_crud(mcp, release_group_id) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_release", {
        "name": "pytest release",
        "description": "test",
        "release_group_id": release_group_id,
    })
    assert "created" in result.content[0].text.lower()
    rid = extract_created_id(result.content[0].text)

    try:
        result = await mcp.call_tool("get_release", {"id": rid})
        assert "pytest release" in result.content[0].text

        result = await mcp.call_tool("update_release", {"id": rid, "name": "pytest rel UPDATED"})
        assert "updated" in result.content[0].text.lower()

        result = await mcp.call_tool("list_releases", {})
        assert rid in result.content[0].text
    finally:
        result = await mcp.call_tool("delete_release", {"id": rid})
        assert "deleted" in result.content[0].text.lower()


async def test_feature_release_assignment(mcp, product_id, release_group_id) -> None:  # type: ignore[no-untyped-def]
    r1 = await mcp.call_tool("create_feature", {
        "name": "pytest assign feat",
        "description": "test",
        "parent_product_id": product_id,
        "status_name": "New idea",
        "feature_type": "feature",
    })
    fid = extract_created_id(r1.content[0].text)

    r2 = await mcp.call_tool("create_release", {
        "name": "pytest assign rel",
        "description": "test",
        "release_group_id": release_group_id,
    })
    rid = extract_created_id(r2.content[0].text)

    try:
        result = await mcp.call_tool("assign_feature_to_release", {
            "feature_id": fid,
            "release_id": rid,
            "assigned": True,
        })
        assert "assigned to" in result.content[0].text.lower()

        result = await mcp.call_tool("list_feature_release_assignments", {"feature_id": fid})
        assert rid in result.content[0].text

        result = await mcp.call_tool("assign_feature_to_release", {
            "feature_id": fid,
            "release_id": rid,
            "assigned": False,
        })
        assert "unassigned" in result.content[0].text.lower()
    finally:
        await mcp.call_tool("delete_release", {"id": rid})
        await mcp.call_tool("delete_feature", {"id": fid})
