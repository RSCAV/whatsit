"""Drives the Swift worker. Python opens every file; the worker only ever sees bytes.

That split is deliberate. macOS keys file-access grants to the binary's absolute path
when it is ad-hoc signed, so a worker that opened paths itself would lose Full Disk
Access on every version bump. Keeping reads here means the grant follows the stable
entry point instead.
"""
import json, os, subprocess, sys
from pathlib import Path

HELPER = Path(__file__).parent / "bin" / "whatsit-ocr"
MAX_BYTES = 40 * 1024 * 1024

def available():
    return HELPER.exists() and os.access(HELPER, os.X_OK)

def _worker(paths, langs):
    proc = subprocess.Popen([str(HELPER), "--langs", langs],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    results = {}
    try:
        for path in paths:
            try:
                data = Path(path).read_bytes()
            except PermissionError:
                raise
            except OSError:
                continue
            if not data or len(data) > MAX_BYTES:
                continue
            proc.stdin.write(f"{len(data)}\n".encode())
            proc.stdin.write(data)
            proc.stdin.flush()
            line = proc.stdout.readline()
            if not line:
                break
            try:
                results[path] = json.loads(line)
            except ValueError:
                continue
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.wait(timeout=30)
    return results

def run(paths, langs="es-ES,en-US", workers=8, progress=None):
    if not available():
        return {}
    from concurrent.futures import ThreadPoolExecutor
    shards = [paths[i::workers] for i in range(workers)]
    out = {}
    with ThreadPoolExecutor(workers) as pool:
        for part in pool.map(lambda s: _worker(s, langs), [s for s in shards if s]):
            out.update(part)
            if progress:
                progress(len(out))
    return out
