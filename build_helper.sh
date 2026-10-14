#!/bin/sh
# macos13.0 is explicit: Command Line Tools 16.x otherwise defaults to macosx16.0,
# which silently makes the binary require macOS 26.
set -e
OUT="${1:-src/whatsit/bin/whatsit-ocr}"
mkdir -p "$(dirname "$OUT")"
swiftc -O -target arm64-apple-macos13.0 -o "$OUT" helper/ocr.swift
codesign -s - --force "$OUT" 2>/dev/null || true
echo "built $OUT"
