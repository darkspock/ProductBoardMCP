"""Productboard MCP Server — built with FastMCP.

Covers the official Productboard API v1 for product team operations:
features, products, components, notes, objectives, key results,
initiatives, releases, release groups, custom fields, and companies.
"""

from fastmcp import FastMCP
from pydantic import Field
from typing import Any, Literal

from src import api
from src.helpers import strip_html, to_html, handle_api_errors

mcp = FastMCP(
    "Productboard",
    instructions=(
        "Access Productboard data for product management: features, products, "
        "components, notes, objectives, key results, initiatives, releases, "
        "custom fields, and companies."
    ),
)


# ───────────────────────────────────────────────────────────────────────────
# Pagination helper
# ───────────────────────────────────────────────────────────────────────────


async def _paginated_get(path: str, params: dict[str, Any] | None = None, max_pages: int = 5) -> list[dict[str, Any]]:
    """Fetch paginated results, following pageCursor links."""
    params = dict(params or {})
    params.setdefault("pageLimit", 100)
    all_items: list[dict[str, Any]] = []
    for _ in range(max_pages):
        data = await api.get(path, params)
        all_items.extend(data.get("data", []))
        cursor = data.get("links", {}).get("next")
        if not cursor:
            break
        # next link is a full URL; extract cursor param
        if "pageCursor=" in str(cursor):
            params["pageCursor"] = str(cursor).split("pageCursor=")[-1].split("&")[0]
        else:
            break
    return all_items


# ───────────────────────────────────────────────────────────────────────────
# Features
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_features(
    status_name: str | None = Field(None, description="Filter by status name (e.g. 'In Progress')"),
    status_id: str | None = Field(None, description="Filter by status UUID"),
    parent_id: str | None = Field(None, description="Filter by parent product/component/feature ID"),
    owner_email: str | None = Field(None, description="Filter by owner email"),
    archived: bool | None = Field(None, description="Filter by archived flag"),
) -> str:
    """List Productboard features with optional filtering."""
    params: dict[str, Any] = {}
    if status_name:
        params["status.name"] = status_name
    if status_id:
        params["status.id"] = status_id
    if parent_id:
        params["parent.id"] = parent_id
    if owner_email:
        params["owner.email"] = owner_email
    if archived is not None:
        params["archived"] = str(archived).lower()

    features = await _paginated_get("/features", params)

    if not features:
        return "No features found."

    lines = [f"Found {len(features)} features:\n"]
    for i, f in enumerate(features, 1):
        name = f.get("name", "Untitled")
        status = f.get("status", {})
        status_str = status.get("name", "Unknown") if isinstance(status, dict) else str(status)
        owner = f.get("owner", {})
        owner_str = owner.get("email", "Unassigned") if isinstance(owner, dict) else "Unassigned"
        desc = strip_html(f.get("description", ""))[:200] if f.get("description") else "No description"
        html_link = f.get("links", {}).get("html", "")
        lines.append(
            f"{i}. {name}\n"
            f"   ID: {f['id']}\n"
            f"   Status: {status_str}\n"
            f"   Owner: {owner_str}\n"
            f"   Description: {desc}"
            + (f"\n   Link: {html_link}" if html_link else "")
        )
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_feature(
    id: str = Field(description="Feature UUID"),
) -> str:
    """Get detailed information about a specific feature."""
    data = await api.get(f"/features/{id}")
    f = data.get("data", data)
    name = f.get("name", "Untitled")
    desc = f.get("description", "")
    status = f.get("status", {})
    owner = f.get("owner") or {}
    parent = f.get("parent") or {}
    timeframe = f.get("timeframe") or {}
    links = f.get("links") or {}

    lines = [
        f"Feature: {name}",
        f"ID: {f.get('id', id)}",
        f"Type: {f.get('type', 'feature')}",
        f"Status: {status.get('name', 'Unknown')} (ID: {status.get('id', 'N/A')})",
        f"Owner: {owner.get('email', 'Unassigned') if isinstance(owner, dict) else 'Unassigned'}",
        f"Archived: {f.get('archived', False)}",
    ]
    if parent:
        for key in ("product", "component", "feature"):
            if key in parent:
                lines.append(f"Parent {key}: {parent[key].get('id', 'N/A')}")
    if timeframe:
        lines.append(f"Timeframe: {timeframe.get('startDate', '?')} to {timeframe.get('endDate', '?')} ({timeframe.get('granularity', '')})")
    if desc:
        lines.append(f"Description: {strip_html(desc)}")
    if links.get("html"):
        lines.append(f"Link: {links['html']}")
    lines.append(f"Created: {f.get('createdAt', 'N/A')}")
    lines.append(f"Updated: {f.get('updatedAt', 'N/A')}")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def create_feature(
    name: str = Field(description="Feature name (max 255 chars)"),
    description: str = Field(description="Feature description (HTML or plain text)"),
    parent_product_id: str | None = Field(None, description="Parent product UUID"),
    parent_component_id: str | None = Field(None, description="Parent component UUID"),
    parent_feature_id: str | None = Field(None, description="Parent feature UUID (for subfeatures)"),
    status_name: str | None = Field(None, description="Status name (e.g. 'New')"),
    status_id: str | None = Field(None, description="Status UUID"),
    feature_type: Literal["feature", "subfeature"] = Field("feature", description="Feature type"),
    owner_email: str | None = Field(None, description="Owner email"),
) -> str:
    """Create a new feature in Productboard."""
    body: dict[str, Any] = {
        "data": {
            "name": name,
            "description": to_html(description),
            "type": feature_type,
        }
    }

    # Parent (required by API)
    if parent_feature_id:
        body["data"]["parent"] = {"feature": {"id": parent_feature_id}}
    elif parent_component_id:
        body["data"]["parent"] = {"component": {"id": parent_component_id}}
    elif parent_product_id:
        body["data"]["parent"] = {"product": {"id": parent_product_id}}

    # Status
    if status_id:
        body["data"]["status"] = {"id": status_id}
    elif status_name:
        body["data"]["status"] = {"name": status_name}

    if owner_email:
        body["data"]["owner"] = {"email": owner_email}

    data = await api.post("/features", body)
    fid = data.get("data", {}).get("id", "unknown")
    html = data.get("data", {}).get("links", {}).get("html", "")
    return f"Feature created. ID: {fid}" + (f"\nLink: {html}" if html else "")


@mcp.tool()
@handle_api_errors
async def update_feature(
    id: str = Field(description="Feature UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
    status_name: str | None = Field(None, description="Status name"),
    status_id: str | None = Field(None, description="Status UUID"),
    owner_email: str | None = Field(None, description="Owner email"),
    archived: bool | None = Field(None, description="Archive flag"),
    parent_product_id: str | None = Field(None, description="Move to product"),
    parent_component_id: str | None = Field(None, description="Move to component"),
    parent_feature_id: str | None = Field(None, description="Move under feature"),
) -> str:
    """Update an existing feature."""
    body: dict[str, Any] = {"data": {}}
    if name:
        body["data"]["name"] = name
    if description:
        body["data"]["description"] = to_html(description)
    if status_id:
        body["data"]["status"] = {"id": status_id}
    elif status_name:
        body["data"]["status"] = {"name": status_name}
    if owner_email:
        body["data"]["owner"] = {"email": owner_email}
    if archived is not None:
        body["data"]["archived"] = archived
    if parent_feature_id:
        body["data"]["parent"] = {"feature": {"id": parent_feature_id}}
    elif parent_component_id:
        body["data"]["parent"] = {"component": {"id": parent_component_id}}
    elif parent_product_id:
        body["data"]["parent"] = {"product": {"id": parent_product_id}}

    if not body["data"]:
        return "Error: at least one field must be provided."

    await api.patch(f"/features/{id}", body)
    return f"Feature {id} updated."


@mcp.tool()
@handle_api_errors
async def delete_feature(
    id: str = Field(description="Feature UUID"),
) -> str:
    """Delete a feature permanently."""
    await api.delete(f"/features/{id}")
    return f"Feature {id} deleted."


@mcp.tool()
@handle_api_errors
async def list_feature_statuses() -> str:
    """List all available feature statuses in the workspace."""
    data = await api.get("/feature-statuses")
    statuses = data.get("data", [])
    if not statuses:
        return "No feature statuses found."
    lines = ["Feature statuses:\n"]
    for s in statuses:
        completed = " (completed)" if s.get("completed") else ""
        lines.append(f"  - {s.get('name', '?')} — ID: {s.get('id', '?')}{completed}")
    return "\n".join(lines)


# Feature links (objectives / initiatives)


@mcp.tool()
@handle_api_errors
async def list_feature_objectives(
    feature_id: str = Field(description="Feature UUID"),
) -> str:
    """List objectives linked to a feature."""
    items = await _paginated_get(f"/features/{feature_id}/links/objectives")
    if not items:
        return "No objectives linked to this feature."
    lines = [f"{len(items)} linked objectives:\n"]
    for o in items:
        lines.append(f"  - {o.get('name', 'Untitled')} (ID: {o.get('id', '?')})")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def link_feature_objective(
    feature_id: str = Field(description="Feature UUID"),
    objective_id: str = Field(description="Objective UUID"),
) -> str:
    """Link a feature to an objective."""
    await api.post(f"/features/{feature_id}/links/objectives/{objective_id}")
    return f"Feature {feature_id} linked to objective {objective_id}."


@mcp.tool()
@handle_api_errors
async def unlink_feature_objective(
    feature_id: str = Field(description="Feature UUID"),
    objective_id: str = Field(description="Objective UUID"),
) -> str:
    """Remove link between a feature and an objective."""
    await api.delete(f"/features/{feature_id}/links/objectives/{objective_id}")
    return f"Feature {feature_id} unlinked from objective {objective_id}."


@mcp.tool()
@handle_api_errors
async def list_feature_initiatives(
    feature_id: str = Field(description="Feature UUID"),
) -> str:
    """List initiatives linked to a feature."""
    items = await _paginated_get(f"/features/{feature_id}/links/initiatives")
    if not items:
        return "No initiatives linked to this feature."
    lines = [f"{len(items)} linked initiatives:\n"]
    for o in items:
        lines.append(f"  - {o.get('name', 'Untitled')} (ID: {o.get('id', '?')})")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def link_feature_initiative(
    feature_id: str = Field(description="Feature UUID"),
    initiative_id: str = Field(description="Initiative UUID"),
) -> str:
    """Link a feature to an initiative."""
    await api.post(f"/features/{feature_id}/links/initiatives/{initiative_id}")
    return f"Feature {feature_id} linked to initiative {initiative_id}."


@mcp.tool()
@handle_api_errors
async def unlink_feature_initiative(
    feature_id: str = Field(description="Feature UUID"),
    initiative_id: str = Field(description="Initiative UUID"),
) -> str:
    """Remove link between a feature and an initiative."""
    await api.delete(f"/features/{feature_id}/links/initiatives/{initiative_id}")
    return f"Feature {feature_id} unlinked from initiative {initiative_id}."


# ───────────────────────────────────────────────────────────────────────────
# Products
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_products() -> str:
    """List all products."""
    products = await _paginated_get("/products")
    if not products:
        return "No products found."
    lines = [f"Found {len(products)} products:\n"]
    for i, p in enumerate(products, 1):
        name = p.get("name", "Untitled")
        desc = strip_html(p.get("description", ""))[:120] if p.get("description") else ""
        lines.append(f"{i}. {name}\n   ID: {p['id']}" + (f"\n   Description: {desc}" if desc else ""))
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_product(
    id: str = Field(description="Product UUID"),
) -> str:
    """Get product details."""
    data = await api.get(f"/products/{id}")
    p = data.get("data", data)
    return (
        f"Product: {p.get('name', 'Untitled')}\n"
        f"ID: {p.get('id', id)}\n"
        f"Description: {strip_html(p.get('description', ''))}\n"
        f"Link: {p.get('links', {}).get('html', 'N/A')}"
    )


@mcp.tool()
@handle_api_errors
async def update_product(
    id: str = Field(description="Product UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
) -> str:
    """Update a product."""
    body: dict[str, Any] = {"data": {}}
    if name:
        body["data"]["name"] = name
    if description:
        body["data"]["description"] = to_html(description)
    if not body["data"]:
        return "Error: at least one field must be provided."
    await api.patch(f"/products/{id}", body)
    return f"Product {id} updated."


# ───────────────────────────────────────────────────────────────────────────
# Components
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_components() -> str:
    """List all components."""
    components = await _paginated_get("/components")
    if not components:
        return "No components found."
    lines = [f"Found {len(components)} components:\n"]
    for i, c in enumerate(components, 1):
        name = c.get("name", "Untitled")
        parent = c.get("parent", {})
        parent_info = ""
        for key in ("product", "component"):
            if key in parent:
                parent_info = f" (parent {key}: {parent[key].get('id', '?')})"
        lines.append(f"{i}. {name}\n   ID: {c['id']}{parent_info}")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_component(
    id: str = Field(description="Component UUID"),
) -> str:
    """Get component details."""
    data = await api.get(f"/components/{id}")
    c = data.get("data", data)
    return (
        f"Component: {c.get('name', 'Untitled')}\n"
        f"ID: {c.get('id', id)}\n"
        f"Description: {strip_html(c.get('description', ''))}"
    )


@mcp.tool()
@handle_api_errors
async def create_component(
    name: str = Field(description="Component name"),
    description: str = Field(description="Component description"),
    parent_product_id: str | None = Field(None, description="Parent product UUID"),
    parent_component_id: str | None = Field(None, description="Parent component UUID"),
    owner_email: str | None = Field(None, description="Owner email"),
) -> str:
    """Create a new component."""
    body: dict[str, Any] = {
        "data": {
            "name": name,
            "description": to_html(description),
        }
    }
    if parent_component_id:
        body["data"]["parent"] = {"component": {"id": parent_component_id}}
    elif parent_product_id:
        body["data"]["parent"] = {"product": {"id": parent_product_id}}

    if owner_email:
        body["data"]["owner"] = {"email": owner_email}

    data = await api.post("/components", body)
    cid = data.get("data", {}).get("id", "unknown")
    return f"Component created. ID: {cid}"


@mcp.tool()
@handle_api_errors
async def update_component(
    id: str = Field(description="Component UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
) -> str:
    """Update a component."""
    body: dict[str, Any] = {"data": {}}
    if name:
        body["data"]["name"] = name
    if description:
        body["data"]["description"] = to_html(description)
    if not body["data"]:
        return "Error: at least one field must be provided."
    await api.patch(f"/components/{id}", body)
    return f"Component {id} updated."


# ───────────────────────────────────────────────────────────────────────────
# Notes
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_notes(
    feature_id: str | None = Field(None, description="Filter by linked feature ID"),
    company_id: str | None = Field(None, description="Filter by company ID"),
    owner_email: str | None = Field(None, description="Filter by owner email"),
    source_system: str | None = Field(None, description="Filter by source system"),
    tags: str | None = Field(None, description="Filter by tags (comma-separated, all must match)"),
    term: str | None = Field(None, description="Search term"),
    created_from: str | None = Field(None, description="Notes created after (ISO date)"),
    created_to: str | None = Field(None, description="Notes created before (ISO date)"),
) -> str:
    """List customer feedback notes with filters."""
    params: dict[str, Any] = {}
    if feature_id:
        params["featureId"] = feature_id
    if company_id:
        params["companyId"] = company_id
    if owner_email:
        params["ownerEmail"] = owner_email
    if source_system:
        params["source"] = source_system
    if tags:
        params["allTags"] = tags
    if term:
        params["term"] = term
    if created_from:
        params["createdFrom"] = created_from
    if created_to:
        params["createdTo"] = created_to

    notes = await _paginated_get("/notes", params)
    if not notes:
        return "No notes found."

    lines = [f"Found {len(notes)} notes:\n"]
    for i, n in enumerate(notes, 1):
        title = n.get("title", "Untitled")
        content = strip_html(n.get("content", ""))[:150] if n.get("content") else ""
        owner = n.get("owner", {})
        owner_str = owner.get("email", "Unknown") if isinstance(owner, dict) else "Unknown"
        tags_list = [t.get("name", t) if isinstance(t, dict) else str(t) for t in (n.get("tags", []) or [])]
        lines.append(
            f"{i}. {title}\n"
            f"   ID: {n.get('id', '?')}\n"
            f"   Owner: {owner_str}\n"
            f"   Content: {content}"
            + (f"\n   Tags: {', '.join(tags_list)}" if tags_list else "")
        )
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_note(
    id: str = Field(description="Note UUID"),
) -> str:
    """Get detailed information about a note."""
    data = await api.get(f"/notes/{id}")
    n = data.get("data", data)
    title = n.get("title", "Untitled")
    content = strip_html(n.get("content", "")) if n.get("content") else ""
    owner = n.get("owner", {})
    tags_list = [t.get("name", t) if isinstance(t, dict) else str(t) for t in (n.get("tags", []) or [])]
    company = n.get("company", {})
    user = n.get("user", {})

    lines = [
        f"Note: {title}",
        f"ID: {n.get('id', id)}",
        f"Owner: {owner.get('email', 'Unknown') if isinstance(owner, dict) else 'Unknown'}",
        f"State: {n.get('state', 'N/A')}",
    ]
    if company:
        lines.append(f"Company: {company.get('name', company.get('id', 'N/A'))}")
    if user:
        lines.append(f"User: {user.get('email', 'N/A')}")
    if tags_list:
        lines.append(f"Tags: {', '.join(tags_list)}")
    lines.append(f"Created: {n.get('createdAt', 'N/A')}")
    if content:
        lines.append(f"Content: {content}")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def create_note(
    title: str = Field(description="Note title"),
    content: str = Field(description="Note content (HTML or plain text)"),
    owner_email: str | None = Field(None, description="Owner email"),
    company_domain: str | None = Field(None, description="Company domain (e.g. acme.com)"),
    user_email: str | None = Field(None, description="Customer user email"),
    source_system: str | None = Field(None, description="Source system name"),
    tags: list[str] | None = Field(None, description="Tags to add"),
) -> str:
    """Create a customer feedback note."""
    body: dict[str, Any] = {
        "title": title,
        "content": to_html(content),
    }
    if owner_email:
        body["owner"] = {"email": owner_email}
    if company_domain:
        body["company"] = {"domain": company_domain}
    if user_email:
        body["user"] = {"email": user_email}
    if source_system:
        body["source"] = {"system": source_system}
    if tags:
        body["tags"] = tags

    data = await api.post("/notes", body)
    nid = data.get("data", {}).get("id", "unknown")
    return f"Note created. ID: {nid}"


@mcp.tool()
@handle_api_errors
async def update_note(
    id: str = Field(description="Note UUID"),
    title: str | None = Field(None, description="New title"),
    content: str | None = Field(None, description="New content"),
    tags: list[str] | None = Field(None, description="Replace all tags"),
) -> str:
    """Update an existing note."""
    data: dict[str, Any] = {}
    if title:
        data["title"] = title
    if content:
        data["content"] = to_html(content)
    if tags is not None:
        data["tags"] = tags
    if not data:
        return "Error: at least one field must be provided."
    await api.patch(f"/notes/{id}", {"data": data})
    return f"Note {id} updated."


@mcp.tool()
@handle_api_errors
async def delete_note(
    id: str = Field(description="Note UUID"),
) -> str:
    """Delete a note."""
    await api.delete(f"/notes/{id}")
    return f"Note {id} deleted."


# ───────────────────────────────────────────────────────────────────────────
# Objectives
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_objectives() -> str:
    """List all objectives."""
    objectives = await _paginated_get("/objectives")
    if not objectives:
        return "No objectives found."

    lines = [f"Found {len(objectives)} objectives:\n"]
    for i, o in enumerate(objectives, 1):
        name = o.get("name", "Untitled")
        owner = o.get("owner", {})
        owner_str = owner.get("email", "Unassigned") if isinstance(owner, dict) else "Unassigned"
        state = o.get("state", "")
        status = o.get("status", {})
        status_str = status.get("name", "") if isinstance(status, dict) else ""
        desc = strip_html(o.get("description", ""))[:120] if o.get("description") else ""
        timeframe = o.get("timeframe", {})
        tf_str = f"{timeframe.get('startDate', '?')} to {timeframe.get('endDate', '?')}" if timeframe and timeframe.get("startDate") else ""
        lines.append(
            f"{i}. {name}\n"
            f"   ID: {o['id']}\n"
            f"   Owner: {owner_str}"
            + (f"\n   Status: {status_str}" if status_str else "")
            + (f"\n   State: {state}" if state else "")
            + (f"\n   Timeframe: {tf_str}" if tf_str else "")
            + (f"\n   Description: {desc}" if desc else "")
        )
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_objective(
    id: str = Field(description="Objective UUID"),
) -> str:
    """Get objective details."""
    data = await api.get(f"/objectives/{id}")
    o = data.get("data", data)
    lines = [
        f"Objective: {o.get('name', 'Untitled')}",
        f"ID: {o.get('id', id)}",
        f"Owner: {(o.get('owner') or {}).get('email', 'Unassigned')}",
        f"State: {o.get('state', 'N/A')}",
        f"Archived: {o.get('archived', False)}",
    ]
    status = o.get("status", {})
    if isinstance(status, dict) and status.get("name"):
        lines.append(f"Status: {status['name']} (ID: {status.get('id', 'N/A')})")
    timeframe = o.get("timeframe", {})
    if timeframe and timeframe.get("startDate"):
        lines.append(f"Timeframe: {timeframe.get('startDate', '?')} to {timeframe.get('endDate', '?')}")
    desc = o.get("description", "")
    if desc:
        lines.append(f"Description: {strip_html(desc)}")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def create_objective(
    name: str = Field(description="Objective name"),
    description: str | None = Field(None, description="Description (HTML or plain text)"),
    owner_email: str | None = Field(None, description="Owner email"),
    status_name: str | None = Field(None, description="Status name"),
    status_id: str | None = Field(None, description="Status UUID"),
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)"),
    parent_objective_id: str | None = Field(None, description="Parent objective UUID (for sub-objectives)"),
) -> str:
    """Create a new objective."""
    body: dict[str, Any] = {"data": {"name": name}}
    if description:
        body["data"]["description"] = to_html(description)
    if owner_email:
        body["data"]["owner"] = {"email": owner_email}
    if status_id:
        body["data"]["status"] = {"id": status_id}
    elif status_name:
        body["data"]["status"] = {"name": status_name}
    if start_date or end_date:
        body["data"]["timeframe"] = {}
        if start_date:
            body["data"]["timeframe"]["startDate"] = start_date
        if end_date:
            body["data"]["timeframe"]["endDate"] = end_date
    if parent_objective_id:
        body["data"]["parent"] = {"objective": {"id": parent_objective_id}}

    data = await api.post("/objectives", body)
    oid = data.get("data", {}).get("id", "unknown")
    return f"Objective created. ID: {oid}"


@mcp.tool()
@handle_api_errors
async def update_objective(
    id: str = Field(description="Objective UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
    owner_email: str | None = Field(None, description="Owner email"),
    status_name: str | None = Field(None, description="Status name"),
    status_id: str | None = Field(None, description="Status UUID"),
    archived: bool | None = Field(None, description="Archive flag"),
    start_date: str | None = Field(None, description="Start date"),
    end_date: str | None = Field(None, description="End date"),
) -> str:
    """Update an existing objective."""
    body: dict[str, Any] = {"data": {}}
    if name:
        body["data"]["name"] = name
    if description:
        body["data"]["description"] = to_html(description)
    if owner_email:
        body["data"]["owner"] = {"email": owner_email}
    if status_id:
        body["data"]["status"] = {"id": status_id}
    elif status_name:
        body["data"]["status"] = {"name": status_name}
    if archived is not None:
        body["data"]["archived"] = archived
    if start_date or end_date:
        body["data"]["timeframe"] = {}
        if start_date:
            body["data"]["timeframe"]["startDate"] = start_date
        if end_date:
            body["data"]["timeframe"]["endDate"] = end_date
    if not body["data"]:
        return "Error: at least one field must be provided."
    await api.patch(f"/objectives/{id}", body)
    return f"Objective {id} updated."


@mcp.tool()
@handle_api_errors
async def delete_objective(
    id: str = Field(description="Objective UUID"),
) -> str:
    """Delete an objective."""
    await api.delete(f"/objectives/{id}")
    return f"Objective {id} deleted."


# Objective links


@mcp.tool()
@handle_api_errors
async def list_objective_features(
    objective_id: str = Field(description="Objective UUID"),
) -> str:
    """List features linked to an objective."""
    items = await _paginated_get(f"/objectives/{objective_id}/links/features")
    if not items:
        return "No features linked to this objective."
    lines = [f"{len(items)} linked features:\n"]
    for f in items:
        lines.append(f"  - {f.get('name', 'Untitled')} (ID: {f.get('id', '?')})")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def list_objective_initiatives(
    objective_id: str = Field(description="Objective UUID"),
) -> str:
    """List initiatives linked to an objective."""
    items = await _paginated_get(f"/objectives/{objective_id}/links/initiatives")
    if not items:
        return "No initiatives linked to this objective."
    lines = [f"{len(items)} linked initiatives:\n"]
    for o in items:
        lines.append(f"  - {o.get('name', 'Untitled')} (ID: {o.get('id', '?')})")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────
# Key Results
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_key_results() -> str:
    """List all key results."""
    key_results = await _paginated_get("/key-results")
    if not key_results:
        return "No key results found."

    lines = [f"Found {len(key_results)} key results:\n"]
    for i, kr in enumerate(key_results, 1):
        name = kr.get("name", "Untitled")
        owner = (kr.get("owner") or {}).get("email", "Unassigned") if isinstance(kr.get("owner"), dict) else "Unassigned"
        progress = kr.get("progress", {})
        current = progress.get("currentValue")
        target = progress.get("targetValue")
        pct = progress.get("progress")
        progress_str = ""
        if current is not None and target is not None:
            progress_str = f" | Progress: {current}/{target}"
            if pct is not None:
                progress_str += f" ({pct}%)"
        parent = kr.get("parent", {})
        parent_id = parent.get("objective", {}).get("id", "?") if isinstance(parent, dict) else "?"
        lines.append(
            f"{i}. {name}\n"
            f"   ID: {kr['id']}\n"
            f"   Owner: {owner}\n"
            f"   Objective: {parent_id}{progress_str}"
        )
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_key_result(
    id: str = Field(description="Key Result UUID"),
) -> str:
    """Get key result details."""
    data = await api.get(f"/key-results/{id}")
    kr = data.get("data", data)
    progress = kr.get("progress", {})
    lines = [
        f"Key Result: {kr.get('name', 'Untitled')}",
        f"ID: {kr.get('id', id)}",
        f"Owner: {(kr.get('owner') or {}).get('email', 'Unassigned')}",
        f"Archived: {kr.get('archived', False)}",
    ]
    if progress:
        lines.append(f"Start value: {progress.get('startValue', 'N/A')}")
        lines.append(f"Current value: {progress.get('currentValue', 'N/A')}")
        lines.append(f"Target value: {progress.get('targetValue', 'N/A')}")
        lines.append(f"Progress: {progress.get('progress', 'N/A')}%")
    parent = kr.get("parent", {})
    if parent:
        lines.append(f"Objective: {parent.get('objective', {}).get('id', 'N/A')}")
    desc = kr.get("description", "")
    if desc:
        lines.append(f"Description: {strip_html(desc)}")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def create_key_result(
    name: str = Field(description="Key result name"),
    parent_objective_id: str = Field(description="Parent objective UUID"),
    description: str | None = Field(None, description="Description"),
    owner_email: str | None = Field(None, description="Owner email"),
    start_value: float | None = Field(None, description="Start value"),
    target_value: float | None = Field(None, description="Target value"),
    current_value: float | None = Field(None, description="Current value"),
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)"),
) -> str:
    """Create a key result for an objective."""
    body: dict[str, Any] = {
        "data": {
            "name": name,
            "parent": {"objective": {"id": parent_objective_id}},
        }
    }
    if description:
        body["data"]["description"] = to_html(description)
    if owner_email:
        body["data"]["owner"] = {"email": owner_email}
    progress: dict[str, Any] = {}
    if start_value is not None:
        progress["startValue"] = start_value
    if target_value is not None:
        progress["targetValue"] = target_value
    if current_value is not None:
        progress["currentValue"] = current_value
    if progress:
        body["data"]["progress"] = progress
    if start_date or end_date:
        body["data"]["timeframe"] = {}
        if start_date:
            body["data"]["timeframe"]["startDate"] = start_date
        if end_date:
            body["data"]["timeframe"]["endDate"] = end_date

    data = await api.post("/key-results", body)
    krid = data.get("data", {}).get("id", "unknown")
    return f"Key result created. ID: {krid}"


@mcp.tool()
@handle_api_errors
async def update_key_result(
    id: str = Field(description="Key Result UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
    owner_email: str | None = Field(None, description="Owner email"),
    start_value: float | None = Field(None, description="Start value"),
    target_value: float | None = Field(None, description="Target value"),
    current_value: float | None = Field(None, description="Current value"),
    archived: bool | None = Field(None, description="Archive flag"),
) -> str:
    """Update a key result."""
    body: dict[str, Any] = {"data": {}}
    if name:
        body["data"]["name"] = name
    if description:
        body["data"]["description"] = to_html(description)
    if owner_email:
        body["data"]["owner"] = {"email": owner_email}
    if archived is not None:
        body["data"]["archived"] = archived
    progress: dict[str, Any] = {}
    if start_value is not None:
        progress["startValue"] = start_value
    if target_value is not None:
        progress["targetValue"] = target_value
    if current_value is not None:
        progress["currentValue"] = current_value
    if progress:
        body["data"]["progress"] = progress
    if not body["data"]:
        return "Error: at least one field must be provided."
    await api.patch(f"/key-results/{id}", body)
    return f"Key result {id} updated."


@mcp.tool()
@handle_api_errors
async def delete_key_result(
    id: str = Field(description="Key Result UUID"),
) -> str:
    """Delete a key result."""
    await api.delete(f"/key-results/{id}")
    return f"Key result {id} deleted."


# ───────────────────────────────────────────────────────────────────────────
# Initiatives
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_initiatives() -> str:
    """List all initiatives."""
    initiatives = await _paginated_get("/initiatives")
    if not initiatives:
        return "No initiatives found."

    lines = [f"Found {len(initiatives)} initiatives:\n"]
    for i, init in enumerate(initiatives, 1):
        name = init.get("name", "Untitled")
        owner = (init.get("owner") or {}).get("email", "Unassigned") if isinstance(init.get("owner"), dict) else "Unassigned"
        status = init.get("status", {})
        status_str = status.get("name", "") if isinstance(status, dict) else ""
        timeframe = init.get("timeframe", {})
        tf_str = f"{timeframe.get('startDate', '?')} to {timeframe.get('endDate', '?')}" if timeframe and timeframe.get("startDate") else ""
        lines.append(
            f"{i}. {name}\n"
            f"   ID: {init['id']}\n"
            f"   Owner: {owner}"
            + (f"\n   Status: {status_str}" if status_str else "")
            + (f"\n   Timeframe: {tf_str}" if tf_str else "")
        )
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_initiative(
    id: str = Field(description="Initiative UUID"),
) -> str:
    """Get initiative details."""
    data = await api.get(f"/initiatives/{id}")
    init = data.get("data", data)
    lines = [
        f"Initiative: {init.get('name', 'Untitled')}",
        f"ID: {init.get('id', id)}",
        f"Owner: {(init.get('owner') or {}).get('email', 'Unassigned')}",
        f"Archived: {init.get('archived', False)}",
    ]
    status = init.get("status", {})
    if isinstance(status, dict) and status.get("name"):
        lines.append(f"Status: {status['name']} (ID: {status.get('id', 'N/A')})")
    timeframe = init.get("timeframe", {})
    if timeframe and timeframe.get("startDate"):
        lines.append(f"Timeframe: {timeframe.get('startDate', '?')} to {timeframe.get('endDate', '?')}")
    desc = init.get("description", "")
    if desc:
        lines.append(f"Description: {strip_html(desc)}")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def create_initiative(
    name: str = Field(description="Initiative name"),
    description: str | None = Field(None, description="Description"),
    owner_email: str | None = Field(None, description="Owner email"),
    status_name: str | None = Field(None, description="Status name"),
    status_id: str | None = Field(None, description="Status UUID"),
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)"),
) -> str:
    """Create a new initiative."""
    body: dict[str, Any] = {"data": {"name": name}}
    if description:
        body["data"]["description"] = to_html(description)
    if owner_email:
        body["data"]["owner"] = {"email": owner_email}
    if status_id:
        body["data"]["status"] = {"id": status_id}
    elif status_name:
        body["data"]["status"] = {"name": status_name}
    if start_date or end_date:
        body["data"]["timeframe"] = {}
        if start_date:
            body["data"]["timeframe"]["startDate"] = start_date
        if end_date:
            body["data"]["timeframe"]["endDate"] = end_date

    data = await api.post("/initiatives", body)
    iid = data.get("data", {}).get("id", "unknown")
    return f"Initiative created. ID: {iid}"


@mcp.tool()
@handle_api_errors
async def update_initiative(
    id: str = Field(description="Initiative UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
    owner_email: str | None = Field(None, description="Owner email"),
    status_name: str | None = Field(None, description="Status name"),
    status_id: str | None = Field(None, description="Status UUID"),
    archived: bool | None = Field(None, description="Archive flag"),
    start_date: str | None = Field(None, description="Start date"),
    end_date: str | None = Field(None, description="End date"),
) -> str:
    """Update an existing initiative."""
    body: dict[str, Any] = {"data": {}}
    if name:
        body["data"]["name"] = name
    if description:
        body["data"]["description"] = to_html(description)
    if owner_email:
        body["data"]["owner"] = {"email": owner_email}
    if status_id:
        body["data"]["status"] = {"id": status_id}
    elif status_name:
        body["data"]["status"] = {"name": status_name}
    if archived is not None:
        body["data"]["archived"] = archived
    if start_date or end_date:
        body["data"]["timeframe"] = {}
        if start_date:
            body["data"]["timeframe"]["startDate"] = start_date
        if end_date:
            body["data"]["timeframe"]["endDate"] = end_date
    if not body["data"]:
        return "Error: at least one field must be provided."
    await api.patch(f"/initiatives/{id}", body)
    return f"Initiative {id} updated."


@mcp.tool()
@handle_api_errors
async def delete_initiative(
    id: str = Field(description="Initiative UUID"),
) -> str:
    """Delete an initiative."""
    await api.delete(f"/initiatives/{id}")
    return f"Initiative {id} deleted."


# Initiative links


@mcp.tool()
@handle_api_errors
async def list_initiative_features(
    initiative_id: str = Field(description="Initiative UUID"),
) -> str:
    """List features linked to an initiative."""
    items = await _paginated_get(f"/initiatives/{initiative_id}/links/features")
    if not items:
        return "No features linked to this initiative."
    lines = [f"{len(items)} linked features:\n"]
    for f in items:
        lines.append(f"  - {f.get('name', 'Untitled')} (ID: {f.get('id', '?')})")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def list_initiative_objectives(
    initiative_id: str = Field(description="Initiative UUID"),
) -> str:
    """List objectives linked to an initiative."""
    items = await _paginated_get(f"/initiatives/{initiative_id}/links/objectives")
    if not items:
        return "No objectives linked to this initiative."
    lines = [f"{len(items)} linked objectives:\n"]
    for o in items:
        lines.append(f"  - {o.get('name', 'Untitled')} (ID: {o.get('id', '?')})")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────
# Releases
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_releases(
    release_group_id: str | None = Field(None, description="Filter by release group UUID"),
) -> str:
    """List releases."""
    params: dict[str, Any] = {}
    if release_group_id:
        params["releaseGroup.id"] = release_group_id

    releases = await _paginated_get("/releases", params)
    if not releases:
        return "No releases found."

    lines = [f"Found {len(releases)} releases:\n"]
    for i, r in enumerate(releases, 1):
        name = r.get("name", "Untitled")
        state = r.get("state", "Unknown")
        group = r.get("releaseGroup", {})
        group_str = group.get("id", "") if isinstance(group, dict) else ""
        timeframe = r.get("timeframe", {})
        tf_str = ""
        if timeframe and timeframe.get("startDate"):
            tf_str = f"{timeframe.get('startDate', '?')} to {timeframe.get('endDate', '?')}"
        lines.append(
            f"{i}. {name}\n"
            f"   ID: {r['id']}\n"
            f"   State: {state}"
            + (f"\n   Release group: {group_str}" if group_str else "")
            + (f"\n   Timeframe: {tf_str}" if tf_str else "")
        )
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_release(
    id: str = Field(description="Release UUID"),
) -> str:
    """Get release details."""
    data = await api.get(f"/releases/{id}")
    r = data.get("data", data)
    lines = [
        f"Release: {r.get('name', 'Untitled')}",
        f"ID: {r.get('id', id)}",
        f"State: {r.get('state', 'N/A')}",
        f"Archived: {r.get('archived', False)}",
    ]
    desc = r.get("description", "")
    if desc:
        lines.append(f"Description: {strip_html(desc)}")
    group = r.get("releaseGroup", {})
    if group:
        lines.append(f"Release group: {group.get('id', 'N/A')}")
    timeframe = r.get("timeframe", {})
    if timeframe and timeframe.get("startDate"):
        lines.append(f"Timeframe: {timeframe.get('startDate', '?')} to {timeframe.get('endDate', '?')}")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def create_release(
    name: str = Field(description="Release name"),
    description: str = Field(description="Release description"),
    release_group_id: str = Field(description="Release group UUID (required — use list_release_groups to find IDs)"),
    state: Literal["upcoming", "completed"] | None = Field(None, description="Release state"),
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)"),
) -> str:
    """Create a new release."""
    body: dict[str, Any] = {
        "data": {
            "name": name,
            "description": to_html(description),
            "releaseGroup": {"id": release_group_id},
        }
    }
    if state:
        body["data"]["state"] = state
    if start_date or end_date:
        body["data"]["timeframe"] = {}
        if start_date:
            body["data"]["timeframe"]["startDate"] = start_date
        if end_date:
            body["data"]["timeframe"]["endDate"] = end_date

    data = await api.post("/releases", body)
    rid = data.get("data", {}).get("id", "unknown")
    return f"Release created. ID: {rid}"


@mcp.tool()
@handle_api_errors
async def update_release(
    id: str = Field(description="Release UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
    state: Literal["upcoming", "completed"] | None = Field(None, description="Release state"),
    archived: bool | None = Field(None, description="Archive flag"),
    start_date: str | None = Field(None, description="Start date"),
    end_date: str | None = Field(None, description="End date"),
) -> str:
    """Update a release."""
    body: dict[str, Any] = {"data": {}}
    if name:
        body["data"]["name"] = name
    if description:
        body["data"]["description"] = to_html(description)
    if state:
        body["data"]["state"] = state
    if archived is not None:
        body["data"]["archived"] = archived
    if start_date or end_date:
        body["data"]["timeframe"] = {}
        if start_date:
            body["data"]["timeframe"]["startDate"] = start_date
        if end_date:
            body["data"]["timeframe"]["endDate"] = end_date
    if not body["data"]:
        return "Error: at least one field must be provided."
    await api.patch(f"/releases/{id}", body)
    return f"Release {id} updated."


@mcp.tool()
@handle_api_errors
async def delete_release(
    id: str = Field(description="Release UUID"),
) -> str:
    """Delete a release."""
    await api.delete(f"/releases/{id}")
    return f"Release {id} deleted."


# ───────────────────────────────────────────────────────────────────────────
# Release Groups
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_release_groups() -> str:
    """List all release groups."""
    groups = await _paginated_get("/release-groups")
    if not groups:
        return "No release groups found."
    lines = [f"Found {len(groups)} release groups:\n"]
    for i, g in enumerate(groups, 1):
        name = g.get("name", "Untitled")
        desc = strip_html(g.get("description", ""))[:120] if g.get("description") else ""
        lines.append(f"{i}. {name}\n   ID: {g['id']}" + (f"\n   Description: {desc}" if desc else ""))
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_release_group(
    id: str = Field(description="Release Group UUID"),
) -> str:
    """Get release group details."""
    data = await api.get(f"/release-groups/{id}")
    g = data.get("data", data)
    return (
        f"Release Group: {g.get('name', 'Untitled')}\n"
        f"ID: {g.get('id', id)}\n"
        f"Archived: {g.get('archived', False)}\n"
        f"Description: {strip_html(g.get('description', ''))}"
    )


@mcp.tool()
@handle_api_errors
async def create_release_group(
    name: str = Field(description="Release group name"),
    description: str = Field(description="Release group description"),
) -> str:
    """Create a new release group."""
    body = {"data": {"name": name, "description": to_html(description)}}
    data = await api.post("/release-groups", body)
    gid = data.get("data", {}).get("id", "unknown")
    return f"Release group created. ID: {gid}"


@mcp.tool()
@handle_api_errors
async def update_release_group(
    id: str = Field(description="Release Group UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
    archived: bool | None = Field(None, description="Archive flag"),
) -> str:
    """Update a release group."""
    body: dict[str, Any] = {"data": {}}
    if name:
        body["data"]["name"] = name
    if description:
        body["data"]["description"] = to_html(description)
    if archived is not None:
        body["data"]["archived"] = archived
    if not body["data"]:
        return "Error: at least one field must be provided."
    await api.patch(f"/release-groups/{id}", body)
    return f"Release group {id} updated."


@mcp.tool()
@handle_api_errors
async def delete_release_group(
    id: str = Field(description="Release Group UUID"),
) -> str:
    """Delete a release group."""
    await api.delete(f"/release-groups/{id}")
    return f"Release group {id} deleted."


# ───────────────────────────────────────────────────────────────────────────
# Feature-Release Assignments
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_feature_release_assignments(
    feature_id: str | None = Field(None, description="Filter by feature UUID"),
    release_id: str | None = Field(None, description="Filter by release UUID"),
    release_state: Literal["upcoming", "completed"] | None = Field(None, description="Filter by release state"),
) -> str:
    """List feature-release assignments."""
    params: dict[str, Any] = {}
    if feature_id:
        params["feature.id"] = feature_id
    if release_id:
        params["release.id"] = release_id
    if release_state:
        params["release.state"] = release_state

    assignments = await _paginated_get("/feature-release-assignments", params)
    if not assignments:
        return "No feature-release assignments found."

    lines = [f"Found {len(assignments)} assignments:\n"]
    for i, a in enumerate(assignments, 1):
        feat = a.get("feature", {})
        rel = a.get("release", {})
        assigned = a.get("assigned", False)
        lines.append(
            f"{i}. Feature: {feat.get('id', '?')} -> Release: {rel.get('id', '?')}\n"
            f"   Assigned: {assigned}"
        )
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def assign_feature_to_release(
    feature_id: str = Field(description="Feature UUID"),
    release_id: str = Field(description="Release UUID"),
    assigned: bool = Field(True, description="True to assign, False to unassign"),
) -> str:
    """Assign or unassign a feature to/from a release."""
    body = {"data": {"assigned": assigned}}
    # Query params must be in the URL for PUT
    path = f"/feature-release-assignments/assignment?feature.id={feature_id}&release.id={release_id}"
    await api.put(path, body)
    action = "assigned to" if assigned else "unassigned from"
    return f"Feature {feature_id} {action} release {release_id}."


# ───────────────────────────────────────────────────────────────────────────
# Custom Fields
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_custom_fields(
    field_type: Literal["text", "number", "dropdown", "multi-dropdown", "member", "custom-description"] | None = Field(None, description="Filter by field type. If omitted, returns all types."),
) -> str:
    """List all custom fields for hierarchy entities (features, products, components)."""
    types_to_query = [field_type] if field_type else ["text", "number", "dropdown", "multi-dropdown", "member", "custom-description"]
    all_fields: list[dict[str, Any]] = []
    for t in types_to_query:
        try:
            data = await api.get("/hierarchy-entities/custom-fields", {"type": t})
            for f in data.get("data", []):
                f["fieldType"] = t
                all_fields.append(f)
        except Exception:
            pass
    if not all_fields:
        return "No custom fields found."
    lines = [f"Found {len(all_fields)} custom fields:\n"]
    for f in all_fields:
        lines.append(f"  - {f.get('name', '?')} (ID: {f.get('id', '?')}, type: {f.get('fieldType', '?')})")
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_custom_field_value(
    custom_field_id: str = Field(description="Custom field UUID"),
    entity_id: str = Field(description="Hierarchy entity UUID (feature, product, or component)"),
) -> str:
    """Get the value of a custom field for a specific entity."""
    params = {"customField.id": custom_field_id, "hierarchyEntity.id": entity_id}
    data = await api.get("/hierarchy-entities/custom-fields-values/value", params)
    value = data.get("data", {}).get("value")
    return f"Custom field value: {value}"


@mcp.tool()
@handle_api_errors
async def set_custom_field_value(
    custom_field_id: str = Field(description="Custom field UUID"),
    entity_id: str = Field(description="Hierarchy entity UUID (feature, product, or component)"),
    field_type: Literal["text", "number", "dropdown", "multi-dropdown", "member", "custom-description"] = Field(description="Custom field type (use list_custom_fields to find types)"),
    value: str = Field(description="Value to set (string, number, or JSON depending on field type)"),
) -> str:
    """Set the value of a custom field for a specific entity."""
    import json as jsonlib
    parsed_value: object = value
    try:
        parsed_value = jsonlib.loads(value)
    except (jsonlib.JSONDecodeError, ValueError):
        pass

    body = {"data": {"type": field_type, "value": parsed_value}}
    await api.put(
        f"/hierarchy-entities/custom-fields-values/value?customField.id={custom_field_id}&hierarchyEntity.id={entity_id}",
        body,
    )
    return f"Custom field {custom_field_id} set to {value} for entity {entity_id}."


# ───────────────────────────────────────────────────────────────────────────
# Companies (read-only)
# ───────────────────────────────────────────────────────────────────────────


@mcp.tool()
@handle_api_errors
async def list_companies(
    term: str | None = Field(None, description="Search term"),
    has_notes: bool | None = Field(None, description="Filter companies with notes"),
    feature_id: str | None = Field(None, description="Filter by associated feature"),
) -> str:
    """List companies (customers) in Productboard."""
    params: dict[str, Any] = {}
    if term:
        params["term"] = term
    if has_notes is not None:
        params["hasNotes"] = str(has_notes).lower()
    if feature_id:
        params["featureId"] = feature_id

    companies = await _paginated_get("/companies", params)
    if not companies:
        return "No companies found."

    lines = [f"Found {len(companies)} companies:\n"]
    for i, c in enumerate(companies, 1):
        name = c.get("name", "Unknown")
        domain = c.get("domain", "")
        lines.append(f"{i}. {name}\n   ID: {c.get('id', '?')}" + (f"\n   Domain: {domain}" if domain else ""))
    return "\n".join(lines)


@mcp.tool()
@handle_api_errors
async def get_company(
    id: str = Field(description="Company UUID"),
) -> str:
    """Get company details."""
    data = await api.get(f"/companies/{id}")
    c = data.get("data", data)
    lines = [
        f"Company: {c.get('name', 'Unknown')}",
        f"ID: {c.get('id', id)}",
    ]
    if c.get("domain"):
        lines.append(f"Domain: {c['domain']}")
    return "\n".join(lines)
