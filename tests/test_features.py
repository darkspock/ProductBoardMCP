"""Integration tests for feature tools."""

import pytest
from tests.helpers import extract_created_id, extract_uuid


@pytest.fixture()
async def feature_id(mcp, product_id):  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_feature", {
        "name": "pytest feature",
        "description": "created by pytest",
        "parent_product_id": product_id,
        "status_name": "New idea",
        "feature_type": "feature",
    })
    fid = extract_created_id(result.content[0].text)
    yield fid
    await mcp.call_tool("delete_feature", {"id": fid})


async def test_list_features(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_features", {})
    assert "features" in result.content[0].text.lower()


async def test_create_get_update_delete_feature(mcp, product_id) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_feature", {
        "name": "pytest CRUD feature",
        "description": "full lifecycle test",
        "parent_product_id": product_id,
        "status_name": "New idea",
        "feature_type": "feature",
    })
    assert "created" in result.content[0].text.lower()
    fid = extract_created_id(result.content[0].text)

    try:
        result = await mcp.call_tool("get_feature", {"id": fid})
        assert "pytest CRUD feature" in result.content[0].text

        result = await mcp.call_tool("update_feature", {"id": fid, "name": "pytest UPDATED"})
        assert "updated" in result.content[0].text.lower()

        result = await mcp.call_tool("get_feature", {"id": fid})
        assert "pytest UPDATED" in result.content[0].text
    finally:
        result = await mcp.call_tool("delete_feature", {"id": fid})
        assert "deleted" in result.content[0].text.lower()


async def test_list_feature_statuses(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_feature_statuses", {})
    text = result.content[0].text
    assert "ID:" in text


async def test_feature_objective_linking(mcp, feature_id) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_objective", {
        "name": "pytest link obj",
        "description": "test",
    })
    obj_id = extract_created_id(result.content[0].text)

    try:
        result = await mcp.call_tool("link_feature_objective", {
            "feature_id": feature_id,
            "objective_id": obj_id,
        })
        assert "linked" in result.content[0].text.lower()

        result = await mcp.call_tool("list_feature_objectives", {"feature_id": feature_id})
        assert obj_id in result.content[0].text

        result = await mcp.call_tool("list_objective_features", {"objective_id": obj_id})
        assert feature_id in result.content[0].text

        result = await mcp.call_tool("unlink_feature_objective", {
            "feature_id": feature_id,
            "objective_id": obj_id,
        })
        assert "unlinked" in result.content[0].text.lower()
    finally:
        await mcp.call_tool("delete_objective", {"id": obj_id})


async def test_feature_initiative_linking(mcp, feature_id) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_initiative", {"name": "pytest link init"})
    text = result.content[0].text
    if text.startswith("Error:"):
        pytest.skip("Initiatives not enabled on this workspace")

    init_id = extract_created_id(text)
    try:
        result = await mcp.call_tool("link_feature_initiative", {
            "feature_id": feature_id,
            "initiative_id": init_id,
        })
        assert "linked" in result.content[0].text.lower()

        result = await mcp.call_tool("unlink_feature_initiative", {
            "feature_id": feature_id,
            "initiative_id": init_id,
        })
        assert "unlinked" in result.content[0].text.lower()
    finally:
        await mcp.call_tool("delete_initiative", {"id": init_id})
