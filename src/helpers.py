"""Shared helpers for tool implementations."""

import functools
import re
from collections.abc import Callable, Coroutine
from typing import Any

from src.api import ProductboardAPIError


def strip_html(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]*>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def to_html(text: str) -> str:
    """Wrap plain text in <p> tags if not already HTML."""
    return text if text.startswith("<") else f"<p>{text}</p>"


def handle_api_errors(fn: Callable[..., Coroutine[Any, Any, str]]) -> Callable[..., Coroutine[Any, Any, str]]:
    """Decorator that catches API errors and returns clean messages."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return await fn(*args, **kwargs)
        except ProductboardAPIError as e:
            if e.status_code == 404:
                return f"Error: resource not found."
            if e.status_code == 401:
                return "Error: authentication failed — check your API token."
            if e.status_code == 403:
                return "Error: insufficient permissions for this operation."
            if e.status_code == 429:
                return "Error: rate limit exceeded — please wait and try again."
            return f"Error: {e}"
        except Exception as e:
            return f"Error: {e}"

    return wrapper
