"""Scan, collapse duplicates, read, label, write."""
import hashlib, os, re, sqlite3, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import ocr, scenes
from .store import connect

IMAGE = {".png", ".jpg", ".jpeg", ".heic", ".webp", ".gif", ".tiff", ".bmp"}
SKIP = ("node_modules", "/.git/", "/Library/", "/.Trash", "/.cache",
        "DerivedData", "/.venv", "__pycache__", "/.whatsit")
HOME = str(Path.home())

def walk(roots):
    seen = set()
    for root in roots:
        root = Path(root).expanduser()
        if root.is_file():
            if root.suffix.lower() in IMAGE:
                yield str(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if any(s in dirpath + "/" for s in SKIP):
                dirnames[:] = []
                continue
            for name in filenames:
                if Path(name).suffix.lower() in IMAGE:
                    p = os.path.join(dirpath, name)
                    if p not in seen:
                        seen.add(p)
                        yield p

def _digest(path):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            head = fh.read(262144)
        return hashlib.blake2b(head + str(size).encode(), digest_size=16).hexdigest(), size
    except OSError:
        return None, 0

def _project(path):
    """The first meaningful folder under home, which is how people already group work."""
    try:
        parts = Path(path).relative_to(HOME).parts[:-1]
    except ValueError:
        parts = Path(path).parts[1:-1]
    for part in parts:
        low = part.lower()
        if low in ("desktop", "downloads", "documents", "pictures", "movies", "music"):
            continue
        return re.sub(r"[^a-z0-9]+", "-", low).strip("-")[:40]
    return ""

def build(roots, langs="es-ES,en-US", say=print):
    say("scanning…")
    files = list(walk(roots))
    say(f"  {len(files):,} images")
    if not files:
        return 0, 0

    say("collapsing duplicates…")
    things = {}
    with ThreadPoolExecutor(16) as pool:
        for path, (digest, size) in zip(files, pool.map(_digest, files)):
            if not digest:
                continue
            thing = things.setdefault(digest, {"paths": [], "bytes": size})
            thing["paths"].append(path)
    reps = [t["paths"][0] for t in things.values()]
    say(f"  {len(things):,} things, {len(files) - len(things):,} duplicate copies folded in")

    say("reading what is printed on them…")
    try:
        read = ocr.run(reps, langs=langs)
    except PermissionError:
        say("\n  macOS blocked reading those files.")
        say("  Give your terminal Full Disk Access in System Settings →")
        say("  Privacy & Security → Full Disk Access, then run this again.\n")
        raise SystemExit(2)
    say(f"  {sum(1 for v in read.values() if (v.get("t") or "").strip()):,} had readable text")

    say("harvesting Apple's own labels…")
    labelled = scenes.for_paths(reps, scenes.vocabulary())
    say(f"  {len(labelled):,} already labelled by macOS")

    db = connect()
    keep = db.execute("SELECT hash, note, at FROM used").fetchall()
    db.executescript("DELETE FROM things; DELETE FROM paths; DELETE FROM fts;")
    rows, fts, pathrows = [], [], []
    for digest, thing in things.items():
        path = thing["paths"][0]
        got = read.get(path, {})
        words, scene = got.get("t", ""), labelled.get(path, "")
        pathwords = re.sub(r"[/_\-.0-9]+", " ", path.replace(HOME, ""))
        rows.append((digest, path, _project(path), words, scene, got.get("w", 0),
                     got.get("h", 0), thing["bytes"], os.path.getmtime(path)
                     if os.path.exists(path) else 0, len(thing["paths"])))
        fts.append((digest, words, scene, pathwords))
        pathrows += [(digest, p) for p in thing["paths"]]
    db.executemany("INSERT INTO things VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
    db.executemany("INSERT INTO paths VALUES(?,?)", pathrows)
    db.executemany("INSERT INTO fts VALUES(?,?,?,?)", fts)
    db.commit()
    return len(things), len(keep)
