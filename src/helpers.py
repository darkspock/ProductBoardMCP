"""Shared helpers for tool implementations."""

import re


def strip_html(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]*>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def to_html(text: str) -> str:
    """Wrap plain text in <p> tags if not already HTML."""
    return text if text.startswith("<") else f"<p>{text}</p>"
