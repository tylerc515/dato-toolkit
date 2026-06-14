"""Shared text search/filter helpers for list pages."""

from __future__ import annotations


def matches_search(query: str, *fields: str) -> bool:
    """Return True if every whitespace-separated term in query appears in some field.

    Matching is case-insensitive and substring-based. An empty (or whitespace-only)
    query matches everything.
    """
    terms = query.lower().split()
    if not terms:
        return True
    haystacks = [field.lower() for field in fields]
    return all(any(term in haystack for haystack in haystacks) for term in terms)
