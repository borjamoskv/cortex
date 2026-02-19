"""
Shared utilities for compaction strategies.
"""
import hashlib
from difflib import SequenceMatcher

def normalize_content(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    return " ".join(text.lower().strip().split())


def content_hash(text: str) -> str:
    """SHA-256 hash of normalized content."""
    return hashlib.sha256(normalize_content(text).encode("utf-8")).hexdigest()


def similarity(a: str, b: str) -> float:
    """Levenshtein-based similarity ratio (0.0–1.0)."""
    return SequenceMatcher(None, normalize_content(a), normalize_content(b)).ratio()


def merge_error_contents(contents: list[str]) -> str:
    """Merge multiple error messages into one consolidated fact."""
    unique_msgs = list(dict.fromkeys(contents))
    if len(unique_msgs) == 1:
        return f"{unique_msgs[0]} (occurred {len(contents)}×)"
    combined = " | ".join(msg[:200] for msg in unique_msgs[:5])
    return f"[Consolidated {len(contents)} errors] {combined}"
