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
    {"name": "catalog_stats",
     "description": "How many things are catalogued and how many carry use-notes.",
     "inputSchema": {"type": "object", "properties": {}}},
]

def _call(name, args):
    if name == "find_file":
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
