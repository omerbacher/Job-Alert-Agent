"""Shared filter logic used by all scrapers."""

CS_KEYWORDS = [
    "computer science", "computer engineering", "software engineering",
    "cs degree", "bsc cs", "b.sc", "\u05ea\u05d5\u05d0\u05e8", "\u05de\u05d3\u05e2\u05d9 \u05d4\u05de\u05d7\u05e9\u05d1\u05d9\u05dd",
]


def passes_cs_filter(description: str) -> bool:
    """Return True if the job should be kept.

    If description is absent or too short we cannot judge — pass it through.
    If description is long enough, at least one CS keyword must appear.
    """
    if not description or len(description) < 100:
        return True
    desc_lower = description.lower()
    return any(kw.lower() in desc_lower for kw in CS_KEYWORDS)
