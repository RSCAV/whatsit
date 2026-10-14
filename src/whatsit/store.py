"""The catalog. One row per thing, not per file."""
import os, sqlite3, datetime
from pathlib import Path

DB_DIR = Path(os.environ.get("WHATSIT_HOME", Path.home() / ".whatsit"))
DB_PATH = DB_DIR / "catalog.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS things(
  hash TEXT PRIMARY KEY, path TEXT, project TEXT, words TEXT, scenes TEXT,
  w INT, h INT, bytes INT, mtime REAL, copies INT);
CREATE TABLE IF NOT EXISTS paths(hash TEXT, path TEXT);
CREATE TABLE IF NOT EXISTS used(hash TEXT, note TEXT, at TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
  hash UNINDEXED, words, scenes, pathwords, tokenize="unicode61");
CREATE INDEX IF NOT EXISTS ipaths ON paths(hash);
CREATE INDEX IF NOT EXISTS iused ON used(hash);
"""

def connect():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    return db

def record_use(db, target, note):
    """Attach provenance to a thing. This is the column no other tool has."""
    row = db.execute(
        "SELECT hash FROM paths WHERE path=? OR path LIKE ? LIMIT 1",
        (target, f"%{target}"),
    ).fetchone()
    if not row:
        return None
    db.execute("INSERT INTO used VALUES(?,?,?)",
               (row[0], note, datetime.date.today().isoformat()))
    db.commit()
    return row[0]
