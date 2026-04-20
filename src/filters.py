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

# For these companies an intern/student title alone is trusted — no CS domain
# word required, because their intern programmes are almost always technical.
PRIORITY_COMPANIES = {
    "nvidia", "intel", "google", "microsoft", "amazon", "meta", "apple",
    "mobileye", "qualcomm", "palo alto networks", "check point",
}


def passes_title_filter(title: str, company: str = "") -> bool:
    """Title must contain an intern/student word.

    For priority companies that's sufficient.
    For all other companies the title must also contain a CS domain word.
    """
    t = title.lower()
    if not any(w in t for w in INTERN_WORDS):
        return False
    if company.lower() in PRIORITY_COMPANIES:
        return True
    return any(kw in t for kw in CS_TITLE_KEYWORDS)


NON_CS_SIGNALS = [
    "physics", "optics", "laser", "mechanical engineering", "chemistry",
    "biology", "electrical engineering", "photonics", "rf ",
    "antenna", "radar", "materials science",
]

CS_DESCRIPTION_SIGNALS = [
    "python", "software", "algorithm", "computer science",
    "machine learning", "backend", "frontend", "cloud", "api",
    "data structures", "programming", "coding", "c++", "java",
    "computer engineering", "information systems",
]


def passes_description_filter(title: str, description: str) -> bool:
    """Reject non-CS roles based on description content.

    Short/absent descriptions get benefit of the doubt.
    Explicit non-CS signals (optics, radar, etc.) reject.
    Explicit CS signals accept. Neither → accept.
    """
    if not description or len(description) < 100:
        return True
    desc_lower = description.lower()
    if any(sig in desc_lower for sig in NON_CS_SIGNALS):
        return False
    if any(sig in desc_lower for sig in CS_DESCRIPTION_SIGNALS):
        return True
    return True


def passes_cs_filter(description: str) -> bool:
    """Return True if the job should be kept.

    If description is absent or too short we cannot judge — pass it through.
    If description is long enough, at least one CS keyword must appear.
    """
    if not description or len(description) < 100:
        return True
    desc_lower = description.lower()
    return any(kw.lower() in desc_lower for kw in CS_KEYWORDS)
