"""Shared filter logic used by all scrapers — two-stage CS relevance."""

INTERN_WORDS = ["intern", "internship", "student"]

CS_SIGNALS = [
    "python", "software", "algorithm", "computer science",
    "machine learning", "backend", "frontend", "cloud", "api",
    "data structures", "programming", "c++", "java", "computer engineering",
    "information systems", "web", "mobile", "devops", "cyber", "security",
    "data science", "artificial intelligence", "neural", "deep learning",
    "database", "sql", "system design", "microservices", "kubernetes", "docker",
    "firmware", "embedded", "hardware", "fpga", "vlsi", "rtl",
    "developer", "engineer", "coding", "fullstack", "full-stack",
]

NON_CS_SIGNALS = [
    "physics", "optics", "laser", "mechanical engineering",
    "chemistry", "biology", "photonics", "antenna", "radar",
    "materials science", "electrical engineering", "accounting",
    "marketing", "supply chain", "graphic design", "economics",
    " sales ", "sales role", "finance role", "legal counsel",
    " hr ", "human resources", "recruitment", "talent acquisition",
]


BLOCKED_TITLE_PHRASES = [
    "practical engineering", "electrical engineering", "mechanical engineering",
    "chemical engineering", "civil engineering", "industrial engineering",
    "materials engineering", "optical engineering", "photonics",
    "laser", "rf engineer", "antenna", "radar", "physics student",
    "chemistry student", "biology student", "economics student",
    "cpa", "accounting", "marketing intern", "sales intern",
    "customer support", "project coordinator", "supply chain",
]

ALLOWED_LOCATIONS = [
    "tel aviv", "herzliya", "raanana", "rehovot", "petah tikva",
    "rishon", "holon", "kfar saba", "netanya", "israel",
    "center district", "central district", "merkaz",
]

BLOCKED_LOCATIONS = [
    "haifa", "beer sheva", "beersheba", "yokneam", "yoqneam",
    "nazareth", "jerusalem", "eilat", "spain", "india", "usa",
    "united states", "uk", "london", "germany", "france",
]


def passes_location_filter(location: str) -> bool:
    """Return True if the location is within the allowed Central Israel area.

    - Blocked location → reject immediately
    - Allowed location → accept
    - Empty or bare "israel" → accept (benefit of the doubt)
    - Specific location not in allowed list → reject
    """
    if not location or not location.strip():
        return True  # no location info — benefit of the doubt
    loc = location.lower().strip()
    if any(b in loc for b in BLOCKED_LOCATIONS):
        return False
    if any(a in loc for a in ALLOWED_LOCATIONS):
        return True
    # Specific location provided but not in allowed list
    return False


def passes_title_filter(title: str) -> bool:
    """Stage 1: title must contain intern / internship / student. No exceptions."""
    t = title.lower()
    if any(phrase in t for phrase in BLOCKED_TITLE_PHRASES):
        return False
    return any(w in t for w in INTERN_WORDS)


def is_cs_relevant(title: str, description: str) -> bool:
    """Stage 2: determine CS relevance.

    With a real description (>100 chars):
      - Non-CS signal present AND no CS signal → reject
      - Any CS signal present → accept
      - Neither found → fall through to title check

    Without a description: title must contain a CS signal.
    """
    if description and len(description) >= 100:
        d = description.lower()
        has_cs    = any(sig in d for sig in CS_SIGNALS)
        has_non_cs = any(sig in d for sig in NON_CS_SIGNALS)
        if has_non_cs and not has_cs:
            return False
        if has_cs:
            return True
        # Neither signal found in description — fall through to title
    # No description or no signal: require a CS keyword in the title
    t = title.lower()
    return any(sig in t for sig in CS_SIGNALS)
