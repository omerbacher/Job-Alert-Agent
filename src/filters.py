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


def passes_title_filter(title: str) -> bool:
    """Stage 1: title must contain intern / internship / student. No exceptions."""
    t = title.lower()
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
