"""Ask in plain words.

Provenance is checked before the bulk index and always outranks it. The `used`
table is small and every row was written by an agent that actually handled the
file, so it is the highest-signal thing in the catalog.
"""
import re
from .store import connect

STOP = {"the", "a", "an", "i", "me", "my", "for", "of", "that", "this", "had",
        "have", "need", "want", "find", "get", "one", "we", "was", "is", "in",
        "on", "to", "it", "and", "with", "from", "png", "jpg", "file", "image",
        "used", "where", "which"}

def terms(question):
    found = re.findall(r"[\w'À-ɏ]+", question.lower())
    return [t for t in found if t not in STOP and len(t) > 1]

def search(question, limit=8, db=None):
    db = db or connect()
    words = terms(question)
    if not words:
        return []

    scores = {}
    for digest, note in db.execute(
            "SELECT hash, group_concat(note, ' | ') FROM used GROUP BY hash"):
        hits = sum(1 for t in words if t in note.lower())
        if hits:
            scores[digest] = -100.0 * hits

    match = " OR ".join(f'"{t}"*' for t in words)
    try:
        bulk = db.execute(
            "SELECT hash, bm25(fts,0,3.0,1.0,2.0) FROM fts WHERE fts MATCH ? LIMIT 400",
            (match,)).fetchall()
    except Exception:
        bulk = []
    for digest, score in bulk:
        scores[digest] = min(scores.get(digest, 99.0), score)
    if not scores:
        return []

    ids = list(scores)
    rows = db.execute(
        f"""SELECT t.hash, t.path, t.project, t.words, t.scenes, t.copies, t.w, t.h,
                   (SELECT group_concat(note, ' | ') FROM used u WHERE u.hash = t.hash)
            FROM things t WHERE t.hash IN ({','.join('?' * len(ids))})""", ids).fetchall()

    out = []
    for digest, path, project, text, scene, copies, w, h, note in rows:
        haystack = f"{text} {scene} {path}".lower()
        hits = sum(1 for t in words if t in haystack)
        out.append({"score": scores[digest] - 6.0 * hits, "path": path,
                    "project": project, "words": text, "scenes": scene,
                    "copies": copies, "w": w, "h": h, "used": note})
    out.sort(key=lambda r: r["score"])
    return out[:limit]
