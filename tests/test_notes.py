"""Integration tests for note tools."""

from tests.helpers import extract_created_id


async def test_note_crud(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("create_note", {
        "title": "pytest note",
        "content": "created by pytest",
    })
    assert "created" in result.content[0].text.lower()
    nid = extract_created_id(result.content[0].text)

    try:
        result = await mcp.call_tool("get_note", {"id": nid})
        assert "pytest note" in result.content[0].text

        result = await mcp.call_tool("update_note", {"id": nid, "title": "pytest UPDATED"})
        assert "updated" in result.content[0].text.lower()

        result = await mcp.call_tool("list_notes", {})
        assert nid in result.content[0].text
    finally:
        result = await mcp.call_tool("delete_note", {"id": nid})
        assert "deleted" in result.content[0].text.lower()


async def test_list_notes_with_filters(mcp) -> None:  # type: ignore[no-untyped-def]
    result = await mcp.call_tool("list_notes", {"term": "sample"})
    # May or may not find results depending on workspace
    assert "note" in result.content[0].text.lower()
