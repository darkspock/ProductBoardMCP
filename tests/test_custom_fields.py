"""Integration tests for custom field and company tools."""

import pytest
from tests.helpers import extract_created_id, extract_uuid


async def test_list_custom_fields(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_custom_fields", {})
    assert "custom field" in result.content[0].text.lower()


async def test_list_custom_fields_by_type(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_custom_fields", {"field_type": "text"})
    text = result.content[0].text
    assert "type: text" in text.lower() or "No custom fields" in text


async def test_set_and_get_custom_field_value(mcp, product_id) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_custom_fields", {"field_type": "text"})
    text = result.content[0].text
    if "No custom fields" in text:
        pytest.skip("No text custom fields in workspace")

    cf_id = extract_uuid(text.split("ID: ", 1)[1])

    result = await mcp.call_tool("create_feature", {
        "name": "pytest cf test",
        "description": "test",
        "parent_product_id": product_id,
        "status_name": "New idea",
        "feature_type": "feature",
    })
    fid = extract_created_id(result.content[0].text)

    try:
        result = await mcp.call_tool("set_custom_field_value", {
            "custom_field_id": cf_id,
            "entity_id": fid,
            "field_type": "text",
            "value": "pytest value",
        })
        assert "set to" in result.content[0].text.lower()

        result = await mcp.call_tool("get_custom_field_value", {
            "custom_field_id": cf_id,
            "entity_id": fid,
        })
        assert "pytest value" in result.content[0].text
    finally:
        await mcp.call_tool("delete_feature", {"id": fid})


async def test_list_companies(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_companies", {})
    assert "compan" in result.content[0].text.lower()


async def test_get_company(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_companies", {})
    text = result.content[0].text
    if "No companies" in text:
        pytest.skip("No companies in workspace")

    co_id = extract_uuid(text.split("ID: ", 1)[1])
    result = await mcp.call_tool("get_company", {"id": co_id})
    assert "Company:" in result.content[0].text
