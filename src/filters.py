"""Shared filter logic used by all scrapers."""

CS_KEYWORDS = [
    "computer science", "computer engineering", "software engineering",
    "cs degree", "bsc cs", "b.sc", "\u05ea\u05d5\u05d0\u05e8", "\u05de\u05d3\u05e2\u05d9 \u05d4\u05de\u05d7\u05e9\u05d1\u05d9\u05dd",
]

CS_TITLE_KEYWORDS = [
    "software", "firmware", "embedded", "backend", "frontend", "developer",
    "engineer", "programmer", "data", "cyber", "security", "network",
    "chip", "silicon", "verification", "hardware", "algorithm", "ml", "ai",
    "cloud", "devops", "full stack", "fullstack", "python", "c++", "r&d",
    "research", "computer", "tech", "coding", "system", "infrastructure",
]

INTERN_WORDS = ["intern", "internship", "student"]


def passes_title_filter(title: str) -> bool:
    """Title must contain a CS domain word AND an intern/student indicator."""
    t = title.lower()
    return (
        any(w in t for w in INTERN_WORDS)
        and any(kw in t for kw in CS_TITLE_KEYWORDS)
    )


def passes_cs_filter(description: str) -> bool:
    """Return True if the job should be kept.

    If description is absent or too short we cannot judge — pass it through.
    If description is long enough, at least one CS keyword must appear.
    """
    if not description or len(description) < 100:
        return True
    desc_lower = description.lower()
    return any(kw.lower() in desc_lower for kw in CS_KEYWORDS)
