"""Slug generation."""

from __future__ import annotations
from slugify import slugify as _slugify


def make_slug(text: str, separator: str = "-") -> str:
    """Convert *text* to a URL-safe slug."""
    return _slugify(text, separator=separator)
