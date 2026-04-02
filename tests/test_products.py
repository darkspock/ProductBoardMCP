"""Integration tests for product and component tools."""

from tests.helpers import extract_created_id


async def test_list_products(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_products", {})
    assert "ID:" in result.content[0].text


async def test_get_product(mcp, product_id) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("get_product", {"id": product_id})
    assert product_id in result.content[0].text


async def test_update_product(mcp, product_id) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("get_product", {"id": product_id})
    original_name = result.content[0].text.split("Product: ")[1].split("\n")[0]

    await mcp.call_tool("update_product", {"id": product_id, "name": "pytest temp"})
    result = await mcp.call_tool("get_product", {"id": product_id})
    assert "pytest temp" in result.content[0].text

    await mcp.call_tool("update_product", {"id": product_id, "name": original_name})


async def test_component_crud(mcp, product_id) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_components", {})
    assert "component" in result.content[0].text.lower()

    result = await mcp.call_tool("create_component", {
        "name": "pytest component",
        "description": "test",
        "parent_product_id": product_id,
    })
    assert "created" in result.content[0].text.lower()
    comp_id = extract_created_id(result.content[0].text)

    result = await mcp.call_tool("get_component", {"id": comp_id})
    assert "pytest component" in result.content[0].text

    result = await mcp.call_tool("update_component", {"id": comp_id, "name": "pytest comp UPDATED"})
    assert "updated" in result.content[0].text.lower()
