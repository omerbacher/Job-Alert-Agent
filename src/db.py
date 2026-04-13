import sqlite3

DB_PATH = "jobs.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id       TEXT PRIMARY KEY,
            title    TEXT,
            company  TEXT,
            location TEXT,
            url      TEXT,
            score    INTEGER,
            date_found TEXT
        )
    """)
    conn.commit()
    conn.close()


def is_seen(job_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return row is not None


def get_recent_jobs(hours: int = 24) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """
        SELECT title, company, location, url, date_found
        FROM jobs
        WHERE date_found >= datetime('now', ?)
        ORDER BY date_found DESC
        """,
        (f"-{hours} hours",),
    ).fetchall()
    conn.close()
    return [
        {"title": r[0], "company": r[1], "location": r[2], "url": r[3], "date_found": r[4]}
        for r in rows
    ]


def save_job(job_id: str, title: str, company: str, location: str, url: str, score: int):
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO jobs (id, title, company, location, url, score, date_found) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (job_id, title, company, location, url, score, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
