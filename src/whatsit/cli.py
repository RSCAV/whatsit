import argparse, os, sys
from pathlib import Path
from . import index
from .search import search
from .store import connect, record_use

HOME = str(Path.home())

def _short(p):
    return p.replace(HOME, "~")

def show(results, question):
    if not results:
        print(f"nothing matches: {question}")
        return 1
    for i, r in enumerate(results, 1):
        print(f"{i}. {_short(r['path'])}")
        bits = [b for b in (r["project"], f"{r['w']}x{r['h']}" if r["w"] else "",
                            f"{r['copies']} copies" if r["copies"] > 1 else "") if b]
        if bits:
            print(f"   {' · '.join(bits)}")
        if r["used"]:
            print(f"   USED FOR: {r['used']}")
        if r["scenes"]:
            print(f"   looks like: {r['scenes'][:84]}")
        if (r["words"] or "").strip():
            print(f"   reads: {r['words'][:108]}")
        print()
    return 0

COMMANDS = {"index", "used", "mcp", "stats"}

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # `whatsit the qr I printed` is the primary form, so anything that is not a
    # known subcommand or flag is treated as the question itself.
    # `-n` is pulled out wherever it sits so the bare-question form keeps working
    # with a leading flag.
    limit = 8
    i = 0
    while i < len(argv):
        if argv[i] in ("-n", "--limit") and i + 1 < len(argv) and argv[i + 1].isdigit():
            limit = int(argv[i + 1])
            del argv[i:i + 2]
        else:
            i += 1

    if argv and argv[0] not in COMMANDS and not argv[0].startswith("-"):
        question = " ".join(argv)
        return show(search(question, limit=limit), question)

    p = argparse.ArgumentParser(
        prog="whatsit", description="Find the file you forgot the name of.")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("index", help="scan folders and build the catalog")
    s.add_argument("roots", nargs="*", default=["~/Desktop", "~/Downloads"])
    s.add_argument("--langs", default="es-ES,en-US")

    u = sub.add_parser("used", help="record what a file was used for")
    u.add_argument("path")
    u.add_argument("note", nargs="+")

    sub.add_parser("mcp", help="run as an MCP server over stdio")
    sub.add_parser("stats", help="what is in the catalog")
    p.add_argument("question", nargs="*", help="ask in plain words")
    p.add_argument("-n", "--limit", type=int, default=8, help="how many results")

    args = p.parse_args(argv)

    if args.cmd == "index":
        things, kept = index.build([os.path.expanduser(r) for r in args.roots],
                                   langs=args.langs)
        noun = "thing" if things == 1 else "things"
        print(f"\n{things:,} {noun} catalogued."
              + (f" {kept} use-notes kept." if kept else ""))
        return 0
    if args.cmd == "used":
        note = " ".join(args.note)
        if record_use(connect(), args.path, note):
            print(f"recorded: {note}")
            return 0
        print(f"not in the catalog: {args.path}")
        return 1
    if args.cmd == "mcp":
        from .server import serve
        return serve()
    if args.cmd == "stats":
        db = connect()
        counts = [
            ("things", "SELECT COUNT(*) FROM things"),
            ("paths", "SELECT COUNT(*) FROM paths"),
            ("with text", "SELECT COUNT(*) FROM things WHERE words != ''"),
            ("with labels", "SELECT COUNT(*) FROM things WHERE scenes != ''"),
            ("use-notes", "SELECT COUNT(*) FROM used"),
        ]
        for label, sql in counts:
            print(f"{label:<14}{db.execute(sql).fetchone()[0]:,}")
        return 0

    if args.question:
        q = " ".join(args.question)
        return show(search(q, limit=limit), q)
    p.print_help()
    return 0
