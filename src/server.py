"""Productboard MCP Server — built with FastMCP."""

from fastmcp import FastMCP
from pydantic import Field
from typing import Literal

from src import api
from src.helpers import strip_html, to_html

mcp = FastMCP(
    "Productboard",
    instructions="Access Productboard data: features, products, notes, objectives, and releases.",
)


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_features(
    status: Literal["new", "in_progress", "validation", "done", "archived"] | None = Field(None, description="Filter by feature status"),
    product_id: str | None = Field(None, description="Filter by product ID"),
    component_id: str | None = Field(None, description="Filter by component ID"),
    owner_email: str | None = Field(None, description="Filter by owner email"),
    search: str | None = Field(None, description="Search in names and descriptions"),
    limit: int = Field(20, description="Max results", ge=1, le=1000),
    offset: int = Field(0, description="Results to skip", ge=0),
) -> str:
    """List Productboard features with optional filtering."""
    params: dict = {"type[]": "feature"}
    if status:
        params["status"] = status
    if product_id:
        params["product_id"] = product_id
    if component_id:
        params["component_id"] = component_id
    if owner_email:
        params["owner_email"] = owner_email
    if search:
        params["search"] = search

    data = await api.get("/entities", params)
    features = data.get("data", [])
    page = features[offset : offset + limit]

    if not page:
        return "No features found."

    lines = [f"Found {len(features)} features, showing {len(page)}:\n"]
    for i, f in enumerate(page, offset + 1):
        fields = f.get("fields", {})
        name = fields.get("name", "Untitled")
        status_name = (fields.get("status") or {}).get("name", "Unknown") if isinstance(fields.get("status"), dict) else fields.get("status", "Unknown")
        owner = (fields.get("owner") or {}).get("email", "Unassigned") if isinstance(fields.get("owner"), dict) else "Unassigned"
        desc = strip_html(fields.get("description", ""))[:200] if fields.get("description") else "No description"
        lines.append(f"{i}. {name}\n   ID: {f['id']}\n   Status: {status_name}\n   Owner: {owner}\n   Description: {desc}")
    return "\n".join(lines)


@mcp.tool()
async def get_feature(
    id: str = Field(description="Feature ID"),
) -> str:
    """Get detailed information about a specific feature."""
    data = await api.get(f"/entities/{id}")
    return str(data)


@mcp.tool()
async def create_feature(
    name: str = Field(description="Feature name (max 255 chars)"),
    description: str = Field(description="Feature description"),
    product_id: str | None = Field(None, description="Parent product ID"),
    component_id: str | None = Field(None, description="Component ID"),
    owner_email: str | None = Field(None, description="Owner email"),
    priority: Literal["critical", "high", "medium", "low"] | None = Field(None, description="Priority level"),
) -> str:
    """Create a new feature in Productboard."""
    fields: dict = {"name": name, "description": to_html(description)}
    if owner_email:
        fields["owner"] = {"email": owner_email}
    if priority:
        fields["priority"] = priority

    relationships = []
    if component_id:
        relationships.append({"type": "parent", "target": {"id": component_id}})
    elif product_id:
        relationships.append({"type": "parent", "target": {"id": product_id}})

    body: dict = {"data": {"type": "feature", "fields": fields}}
    if relationships:
        body["data"]["relationships"] = relationships

    data = await api.post("/entities", body)
    fid = data.get("data", {}).get("id", "unknown")
    return f"Feature created successfully. ID: {fid}"


@mcp.tool()
async def update_feature(
    id: str = Field(description="Feature ID to update"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
    status_id: str | None = Field(None, description="Status ID (UUID from the status object)"),
    owner_email: str | None = Field(None, description="New owner email"),
) -> str:
    """Update an existing feature."""
    fields: dict = {}
    if name:
        fields["name"] = name
    if description:
        fields["description"] = to_html(description)
    if status_id:
        fields["status"] = {"id": status_id}
    if owner_email:
        fields["owner"] = {"email": owner_email}

    if not fields:
        return "Error: at least one field must be provided for update."

    data = await api.patch(f"/entities/{id}", {"data": {"fields": fields}})
    return f"Feature {id} updated successfully."


@mcp.tool()
async def delete_feature(
    id: str = Field(description="Feature ID to delete"),
    permanent: bool = Field(False, description="If true, permanently delete. If false, archive."),
) -> str:
    """Delete or archive a feature."""
    if permanent:
        await api.delete(f"/entities/{id}")
        return f"Feature {id} permanently deleted."
    else:
        await api.patch(f"/entities/{id}", {"data": {"fields": {"archived": True}}})
        return f"Feature {id} archived."


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_products(
    parent_id: str | None = Field(None, description="Filter by parent product ID"),
) -> str:
    """List all products in the workspace."""
    params: dict = {"type[]": "product"}
    if parent_id:
        params["parent_id"] = parent_id

    data = await api.get("/entities", params)
    products = data.get("data", [])

    if not products:
        return "No products found."

    lines = [f"Found {len(products)} products:\n"]
    for i, p in enumerate(products, 1):
        fields = p.get("fields", {})
        name = fields.get("name", "Untitled Product")
        desc = strip_html(fields.get("description", ""))[:120] if fields.get("description") else ""
        lines.append(f"{i}. {name}\n   ID: {p['id']}" + (f"\n   Description: {desc}" if desc else ""))
    return "\n".join(lines)


@mcp.tool()
async def create_product(
    name: str = Field(description="Product name"),
    description: str | None = Field(None, description="Product description"),
    parent_id: str | None = Field(None, description="Parent product ID (for sub-products)"),
    owner_email: str | None = Field(None, description="Product owner email"),
) -> str:
    """Create a new product or sub-product."""
    fields: dict = {"name": name}
    if description:
        fields["description"] = to_html(description)
    if owner_email:
        fields["owner"] = {"email": owner_email}

    relationships = []
    if parent_id:
        relationships.append({"type": "parent", "target": {"id": parent_id}})

    body: dict = {"data": {"type": "product", "fields": fields}}
    if relationships:
        body["data"]["relationships"] = relationships

    data = await api.post("/entities", body)
    pid = data.get("data", {}).get("id", "unknown")
    return f"Product created successfully. ID: {pid}"


@mcp.tool()
async def product_hierarchy(
    product_id: str | None = Field(None, description="Root product ID (omit for all top-level)"),
) -> str:
    """Get the product hierarchy tree."""
    params: dict = {"type[]": "product"}
    if product_id:
        params["parent_id"] = product_id

    data = await api.get("/entities", params)
    products = data.get("data", [])

    if not products:
        return "No products found."

    lines = [f"Product hierarchy ({len(products)} products):\n"]
    for p in products:
        name = p.get("fields", {}).get("name", "Untitled")
        lines.append(f"  - {name} (ID: {p['id']})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_note(
    content: str = Field(description="Note content (customer feedback)"),
    title: str | None = Field(None, description="Note title/summary"),
) -> str:
    """Create a customer feedback note."""
    fields: dict = {
        "name": title or content[:100],
        "content": to_html(content),
    }

    data = await api.post("/notes", {"data": {"type": "simple", "fields": fields}})
    nid = data.get("data", {}).get("id", "unknown")
    return f"Note created successfully. ID: {nid}"


@mcp.tool()
async def list_notes(
    feature_id: str | None = Field(None, description="Filter by linked feature ID"),
    customer_email: str | None = Field(None, description="Filter by customer email"),
    company_name: str | None = Field(None, description="Filter by company"),
    date_from: str | None = Field(None, description="Notes created after this date (YYYY-MM-DD)"),
    date_to: str | None = Field(None, description="Notes created before this date (YYYY-MM-DD)"),
    limit: int = Field(20, description="Max results", ge=1, le=100),
) -> str:
    """List customer feedback notes."""
    params: dict = {}
    if feature_id:
        params["feature_id"] = feature_id
    if customer_email:
        params["customer_email"] = customer_email
    if company_name:
        params["company_name"] = company_name
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    data = await api.get("/notes", params)
    all_notes = data.get("data", [])
    notes = all_notes[:limit]

    if not notes:
        return "No notes found."

    lines = [f"Found {len(all_notes)} notes, showing {len(notes)}:\n"]
    for i, n in enumerate(notes, 1):
        fields = n.get("fields", {})
        title = fields.get("name") or (strip_html(fields.get("content", ""))[:60] if fields.get("content") else "Untitled")
        content = strip_html(fields.get("content", ""))[:150] if fields.get("content") else ""
        owner = (fields.get("owner") or {}).get("email", "Unknown") if isinstance(fields.get("owner"), dict) else "Unknown"
        lines.append(f"{i}. {title}\n   Owner: {owner}\n   Content: {content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Objectives
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_objectives(
    status: Literal["active", "completed", "cancelled"] | None = Field(None, description="Filter by status"),
    owner_email: str | None = Field(None, description="Filter by owner email"),
    limit: int = Field(20, description="Max results", ge=1, le=100),
    offset: int = Field(0, description="Results to skip", ge=0),
) -> str:
    """List objectives with optional filtering."""
    params: dict = {"type[]": "objective"}
    if status:
        params["status"] = status
    if owner_email:
        params["owner_email"] = owner_email

    data = await api.get("/entities", params)
    all_objs = data.get("data", [])
    objs = all_objs[offset : offset + limit]

    if not objs:
        return "No objectives found."

    lines = [f"Found {len(all_objs)} objectives, showing {len(objs)}:\n"]
    for i, o in enumerate(objs, offset + 1):
        fields = o.get("fields", {})
        name = fields.get("name", "Untitled Objective")
        status_val = (fields.get("status") or {}).get("name", "Unknown") if isinstance(fields.get("status"), dict) else str(fields.get("status", "Unknown"))
        owner = (fields.get("owner") or {}).get("email", "Unassigned") if isinstance(fields.get("owner"), dict) else "Unassigned"
        desc = strip_html(fields.get("description", ""))[:120] if fields.get("description") else ""
        lines.append(f"{i}. {name}\n   Status: {status_val}\n   Owner: {owner}" + (f"\n   Description: {desc}" if desc else ""))
    return "\n".join(lines)


@mcp.tool()
async def create_objective(
    name: str = Field(description="Objective name"),
    description: str = Field(description="Objective description"),
    owner_email: str | None = Field(None, description="Owner email"),
) -> str:
    """Create a new objective."""
    fields: dict = {"name": name, "description": to_html(description)}
    if owner_email:
        fields["owner"] = {"email": owner_email}

    data = await api.post("/entities", {"data": {"type": "objective", "fields": fields}})
    oid = data.get("data", {}).get("id", "unknown")
    return f"Objective created successfully. ID: {oid}"


@mcp.tool()
async def update_objective(
    id: str = Field(description="Objective ID to update"),
    name: str | None = Field(None, description="Objective name"),
    description: str | None = Field(None, description="Objective description"),
    status_id: str | None = Field(None, description="Status ID (UUID)"),
    owner_email: str | None = Field(None, description="Owner email"),
) -> str:
    """Update an existing objective."""
    fields: dict = {}
    if name:
        fields["name"] = name
    if description:
        fields["description"] = to_html(description)
    if status_id:
        fields["status"] = {"id": status_id}
    if owner_email:
        fields["owner"] = {"email": owner_email}

    if not fields:
        return "Error: no update fields provided."

    await api.patch(f"/entities/{id}", {"data": {"fields": fields}})
    return f"Objective {id} updated successfully."


# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_releases(
    status: Literal["planned", "in_progress", "released"] | None = Field(None, description="Filter by status"),
    date_from: str | None = Field(None, description="Releases after this date (YYYY-MM-DD)"),
    date_to: str | None = Field(None, description="Releases before this date (YYYY-MM-DD)"),
    limit: int = Field(20, description="Max results", ge=1, le=100),
    offset: int = Field(0, description="Results to skip", ge=0),
) -> str:
    """List releases with optional filtering."""
    params: dict = {"type[]": "release"}
    if status:
        params["status"] = status
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    data = await api.get("/entities", params)
    all_releases = data.get("data", [])
    releases = all_releases[offset : offset + limit]

    if not releases:
        return "No releases found."

    lines = [f"Found {len(all_releases)} releases, showing {len(releases)}:\n"]
    for i, r in enumerate(releases, offset + 1):
        fields = r.get("fields", {})
        name = fields.get("name", "Untitled Release")
        status_val = (fields.get("state") or fields.get("status") or {})
        if isinstance(status_val, dict):
            status_str = status_val.get("name", "Unknown")
        else:
            status_str = str(status_val) if status_val else "Unknown"
        date = fields.get("release_date", "")
        desc = strip_html(fields.get("description", ""))[:150] if fields.get("description") else ""
        line = f"{i}. {name}\n   ID: {r['id']}\n   Status: {status_str}"
        if date:
            line += f"\n   Date: {date}"
        if desc:
            line += f"\n   Description: {desc}"
        lines.append(line)
    return "\n".join(lines)


@mcp.tool()
async def create_release(
    name: str = Field(description="Release name/version"),
    description: str | None = Field(None, description="Release description"),
    release_group_id: str | None = Field(None, description="Parent release group ID"),
) -> str:
    """Create a new release."""
    fields: dict = {"name": name}
    if description:
        fields["description"] = to_html(description)

    relationships = []
    if release_group_id:
        relationships.append({"type": "parent", "target": {"id": release_group_id}})

    body: dict = {"data": {"type": "release", "fields": fields}}
    if relationships:
        body["data"]["relationships"] = relationships

    data = await api.post("/entities", body)
    rid = data.get("data", {}).get("id", "unknown")
    return f"Release created successfully. ID: {rid}"


@mcp.tool()
async def update_release(
    id: str = Field(description="Release ID to update"),
    name: str | None = Field(None, description="Release name"),
    description: str | None = Field(None, description="Release description"),
    status_id: str | None = Field(None, description="Status ID (UUID)"),
    release_group_id: str | None = Field(None, description="Parent release group ID"),
) -> str:
    """Update an existing release."""
    fields: dict = {}
    if name:
        fields["name"] = name
    if description:
        fields["description"] = to_html(description)
    if status_id:
        fields["status"] = {"id": status_id}

    relationships = []
    if release_group_id:
        relationships.append({"type": "parent", "target": {"id": release_group_id}})

    if not fields and not relationships:
        return "Error: no update fields provided."

    body: dict = {"data": {"fields": fields}}
    if relationships:
        body["data"]["relationships"] = relationships

    await api.patch(f"/entities/{id}", body)
    return f"Release {id} updated successfully."


@mcp.tool()
async def release_timeline(
    release_group_id: str | None = Field(None, description="Filter by release group"),
    date_from: str | None = Field(None, description="Start date (YYYY-MM-DD)"),
    date_to: str | None = Field(None, description="End date (YYYY-MM-DD)"),
) -> str:
    """Get release timeline with release groups."""
    params: dict = {"type[]": "releaseGroup"}
    if release_group_id:
        params["release_group_id"] = release_group_id
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    data = await api.get("/entities", params)
    return str(data)


@mcp.tool()
async def release_status_update(
    id: str = Field(description="Release ID"),
    status_id: str = Field(description="Status ID (UUID from the status object on the release)"),
    release_notes: str | None = Field(None, description="Release notes"),
) -> str:
    """Update release status and optionally publish release notes."""
    fields: dict = {"status": {"id": status_id}}
    if release_notes:
        fields["release_notes"] = release_notes

    await api.patch(f"/entities/{id}", {"data": {"fields": fields}})
    return f"Release {id} status updated successfully."
