# whatsit

[![PyPI](https://img.shields.io/pypi/v/whatsit)](https://pypi.org/project/whatsit/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![CI](https://github.com/RSCAV/whatsit/actions/workflows/ci.yml/badge.svg)](https://github.com/RSCAV/whatsit/actions/workflows/ci.yml)

![demo](demo.gif)

Find the file you forgot the name of. `whatsit` reads what is printed inside your
images, keeps one entry per thing instead of per copy, and remembers what each
one was *used* for. Then it hands all of that to whatever AI you work with.

Everything happens on your Mac. Nothing is uploaded, nothing is moved, nothing is
renamed, and there is no account. I built it because 7,686 of my own files were
called things like `Untitled design (3).png` and I was tired of not finding them.

## Install

```bash
uvx whatsit
```

Keep it around with `uv tool install whatsit`, or `pipx install whatsit`.
macOS 13 or later, Apple Silicon.

## Quick start

```bash
whatsit index ~/Desktop ~/Downloads     # once, a few minutes, free
whatsit "the invoice from the printer"  # ask in plain words
```

```
$ whatsit "the QR I printed for the stand"

1. ~/Desktop/QR propiedash-go/propiedash-go-qr-2048.png
   propiedash · 2048x2048
   USED FOR: the QR we printed for the Summit stand sign
```

That last line is the point. It was not written by hand.

## Why this is different

#### ❌ Without

- Spotlight matches letters, so searching `QR` returns `QRJQF.jpg`, a property code.
- Everything that reads your pictures properly wants you to import them into its own library first.
- Nothing anywhere knows which of your six near-identical QR files is the one you actually printed.

#### ✅ With

- One entry per *thing*. 44,767 files on my Mac became 31,021 entries.
- The words printed inside an image are searchable, offline, using Apple's own text recognition.
- An agent records what a file was used for while doing the work, and that is what makes it findable later.

## Use it from Claude, Cursor, Codex

Claude Code:

```bash
claude mcp add --transport stdio whatsit --scope user -- uvx whatsit mcp
```

Cursor, in `~/.cursor/mcp.json`:

```json
{ "mcpServers": { "whatsit": { "type": "stdio", "command": "uvx", "args": ["whatsit", "mcp"] } } }
```

Codex and the ChatGPT desktop app share `~/.codex/config.toml`:

```toml
[mcp_servers.whatsit]
command = "uvx"
args = ["whatsit", "mcp"]
```

Three tools come across: `find_file`, `record_use` and `catalog_stats`. The one that
matters is `record_use` — point your agent at it and tell it to call it whenever it
makes, prints, publishes or sends a file. The catalog then writes itself.

## How it works

- **Apple's Vision framework** reads the text inside every image, offline, in Spanish and English. About 40 images a second.
- **Apple's own scene labels** are already sitting in Spotlight's metadata for roughly half your pictures, unread by anything. `whatsit` harvests them for free.
- **Byte-identical copies collapse** into one entry with many paths, so twelve copies of a logo are one row.
- **SQLite with FTS5**, one file, nothing to run.

## Numbers from a real Mac

| | |
|---|---|
| Files scanned | 44,767 |
| Things after collapsing copies | 31,021 |
| Most copies of one image | 108 |
| Query time | 103 ms |
| Cost | nothing |

## What it does not do

It sends nothing over the network. It moves nothing. It renames nothing. It deletes
nothing. The catalog lives in `~/.whatsit/catalog.db` and deleting that file undoes
the whole thing.

## Full Disk Access

macOS will ask before letting anything read `~/Desktop` and `~/Documents`. The grant
attaches to your *terminal*, not to `whatsit`, so if indexing stops early, give your
terminal app Full Disk Access in System Settings → Privacy & Security.

## License

MIT
