"""Ask in plain words.

Provenance is checked before the bulk index and always outranks it. The `used`
table is small and every row was written by an agent that actually handled the
file, so it is the highest-signal thing in the catalog.
"""
import re
from pathlib import Path
from .store import connect


def _mentions(term, text):
    """Whole-word match. Substring matching made "app" hit inside "approved"."""
    return re.search(rf"(?<!\w){re.escape(term)}\w{{0,3}}(?!\w)", text) is not None

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
    n = len(words)

    # Provenance is the strongest signal, but only when it answers most of the
    # question. Matching one generic word out of four should not beat a file
    # whose own name matches three.
    scores = {}
    for digest, note in db.execute(
            "SELECT hash, group_concat(DISTINCT note) FROM used GROUP BY hash"):
        hits = sum(1 for t in words if _mentions(t, note.lower()))
        if hits:
            ratio = hits / n
            scores[digest] = -70.0 * ratio * ratio

    # A broad OR over everything, capped. On a common word like a project name
    # this alone truncates before the good answers surface, so it is only the
    # first of two passes.
    match = " OR ".join(f'"{t}"*' for t in words)
    try:
        bulk = db.execute(
            "SELECT hash, bm25(fts,0,3.0,1.0,2.0) FROM fts WHERE fts MATCH ? LIMIT 600",
            (match,)).fetchall()
    except Exception:
        bulk = []
    for digest, score in bulk:
        scores[digest] = min(scores.get(digest, 99.0), score)

    # Second pass: files whose own path contains the words, which is where
    # well-named folders live. Progressively relaxed so something always lands.
    for required in range(len(words), 1, -1):
        expr = " AND ".join(f'pathwords:"{t}"*' for t in words[:required])
        try:
            found = db.execute(
                "SELECT hash FROM fts WHERE fts MATCH ? LIMIT 120", (expr,)).fetchall()
        except Exception:
            found = []
        if found:
            for (digest,) in found:
                scores.setdefault(digest, 0.0)
            break
    if not scores:
        return []

    ids = list(scores)
    rows = db.execute(
        f"""SELECT t.hash, t.path, t.project, t.words, t.scenes, t.copies, t.w, t.h,
                   (SELECT group_concat(DISTINCT note) FROM used u WHERE u.hash = t.hash)
            FROM things t WHERE t.hash IN ({','.join('?' * len(ids))})""", ids).fetchall()

    out = []
    for digest, path, project, text, scene, copies, w, h, note in rows:
        parts = Path(path).parts
        name = " ".join([parts[-1]] + list(parts[-3:-1]) + [project or ""]).lower()
        body, labels = (text or "").lower(), (scene or "").lower()
        prov = (note or "").lower()
        fields = (name, body, labels, path.lower(), prov)

        # How much of the question this file answers at all. A file that covers
        # every word beats one that covers most, whatever the evidence is.
        covered = sum(1 for t in words if any(_mentions(t, f) for f in fields)) / n
        score = -100.0 * covered * covered

        # Then the kind of evidence breaks ties, best evidence first.
        score -= 25.0 * (sum(1 for t in words if _mentions(t, prov)) / n) ** 2
        score -= 15.0 * (sum(1 for t in words if _mentions(t, name)) / n)
        score -= 8.0 * (sum(1 for t in words if _mentions(t, body)) / n)
        score -= 4.0 * (sum(1 for t in words if _mentions(t, labels)) / n)
        score += scores[digest] / 4.0

        out.append({"score": score, "path": path, "project": project,
                    "words": text, "scenes": scene, "copies": copies,
                    "w": w, "h": h, "used": note})
    out.sort(key=lambda r: r["score"])
    return out[:limit]
