"""MCP over stdio. Three tools, which is the whole surface.

Deliberately dependency-free: the protocol is small enough that hand-rolling it
keeps the install to a single wheel with nothing to resolve.
"""
import json, sys
from .search import search
from .store import connect, record_use

TOOLS = [
    {"name": "find_file",
     "description": "Find a file on this Mac by describing it in plain words, "
                    "including what it was used for.",
     "inputSchema": {"type": "object",
                     "properties": {"question": {"type": "string"},
                                    "limit": {"type": "integer", "default": 5}},
                     "required": ["question"]}},
    {"name": "record_use",
     "description": "Record what a file was used for, right after using it. "
                    "Call this whenever you make, print, publish or send a file.",
     "inputSchema": {"type": "object",
                     "properties": {"path": {"type": "string"},
                                    "note": {"type": "string"}},
                     "required": ["path", "note"]}},
    {"name": "index_folders",
     "description": "Build or refresh the catalog from folders on this Mac. Call this "
                    "if find_file reports the catalog is empty. Defaults to the "
                    "Desktop and Downloads folders. Takes a few minutes and is free.",
     "inputSchema": {"type": "object",
                     "properties": {"folders": {"type": "array",
                                                "items": {"type": "string"}}}}},
    {"name": "catalog_stats",
     "description": "How many things are catalogued and how many carry use-notes.",
     "inputSchema": {"type": "object", "properties": {}}},
]

def _is_empty():
    return connect().execute("SELECT COUNT(*) FROM things").fetchone()[0] == 0


def _call(name, args):
    if name == "find_file":
        if _is_empty():
            return ("The catalog is empty, so nothing has been read yet. Ask the user "
                    "whether to index now, and if they agree call index_folders. It "
                    "takes a few minutes, runs entirely on this Mac and costs nothing. "
                    "macOS may ask them to grant Full Disk Access to their terminal.")
        hits = search(args.get("question", ""), limit=int(args.get("limit", 5)))
        if not hits:
            return "No match."
        out = []
        for h in hits:
            line = h["path"]
            if h["used"]:
                line += f"\n    USED FOR: {h['used']}"
            if h["scenes"]:
                line += f"\n    looks like: {h['scenes'][:80]}"
            if (h["words"] or "").strip():
                line += f"\n    reads: {h['words'][:100]}"
            out.append(line)
        return "\n".join(out)
    if name == "record_use":
        ok = record_use(connect(), args.get("path", ""), args.get("note", ""))
        return "Recorded." if ok else "That path is not in the catalog."
    if name == "index_folders":
        import os
        from . import ocr as _ocr
        from .index import build
        if not _ocr.available():
            return ("The text reader is missing, so indexing would catalogue names "
                    "without reading anything. This happens when whatsit is installed "
                    "straight from the git repo. Tell the user to install the published "
                    "package instead, or to clone the repo and run ./build_helper.sh once.")
        folders = args.get("folders") or ["~/Desktop", "~/Downloads"]
        lines = []
        things, kept = build([os.path.expanduser(f) for f in folders],
                             say=lines.append)
        noun = "thing" if things == 1 else "things"
        return (f"{things:,} {noun} catalogued from {', '.join(folders)}."
                + (f" {kept} use-notes kept." if kept else "")
                + "\n" + "\n".join(lines))
    if name == "catalog_stats":
        db = connect()
        things = db.execute("SELECT COUNT(*) FROM things").fetchone()[0]
        notes = db.execute("SELECT COUNT(*) FROM used").fetchone()[0]
        return f"{things} things catalogued, {notes} with a use-note."
    raise ValueError(f"unknown tool {name}")

def serve():
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        method, mid = msg.get("method"), msg.get("id")
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05",
                      "capabilities": {"tools": {}},
                      "serverInfo": {"name": "whatsit", "version": "0.1.0"}}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = msg.get("params", {})
            try:
                text = _call(params.get("name"), params.get("arguments") or {})
                result = {"content": [{"type": "text", "text": text}]}
            except Exception as exc:
                result = {"content": [{"type": "text", "text": str(exc)}],
                          "isError": True}
        elif mid is None:
            continue
        else:
            result = {}
        if mid is not None:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
            sys.stdout.flush()
    return 0
