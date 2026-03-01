"""Type definitions for the fetch tool."""

from enum import Enum


class PageType(Enum):
    """Enumeration for different types of web pages."""
    ARTICLE = "article"
    FORUM = "forum"
    QA = "qa"
    UNKNOWN = "unknown"