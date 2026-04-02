"""Test helpers."""

import re


def extract_uuid(text: str) -> str:
    """Extract the first UUID from text."""
    match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
    if match:
        return match.group(0)
    raise ValueError(f"No UUID found in: {text[:200]}")


def extract_created_id(text: str) -> str:
    """Extract ID from a 'Created. ID: xxx' response."""
    if "ID: " in text:
        after = text.split("ID: ", 1)[1]
        return extract_uuid(after)
    return extract_uuid(text)
