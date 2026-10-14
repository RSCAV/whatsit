"""Apple already labelled about half these images. Nobody reads it, so we do.

The vocabulary ships inside PhotosFormats.framework; the identifiers on each file
look like "1-784" and the trailing field of the matching taxonomy row is the word.
"""
import bz2, json, plistlib, re, subprocess
from pathlib import Path

RES = Path("/System/Library/PrivateFrameworks/PhotosFormats.framework"
           "/Versions/A/Resources")
ATTR = "kMDItemPhotosSceneClassificationTypedIdentifiers"

def vocabulary():
    taxonomy = next(RES.glob("PFSceneTaxonomyData*.bz2"), None)
    if not taxonomy:
        return {}
    raw = bz2.decompress(taxonomy.read_bytes()).decode("utf-8", "replace")
    qid_to_name = {}
    for line in raw.splitlines():
        if line.startswith("d:"):
            _, qid, name = line.split(":", 2)
            qid_to_name[qid] = name
    labels = {}
    for line in raw.splitlines():
        if not line.startswith("n:"):
            continue
        fields = line[2:].split(",")
        node, last = fields[0], fields[-1]
        name = qid_to_name.get(last, last) if last.startswith("Q") else last
        if name and not name.startswith("Q"):
            labels[node] = name
    return labels

def for_paths(paths, labels, batch=60):
    out = {}
    if not labels:
        return out
    for i in range(0, len(paths), batch):
        chunk = paths[i:i + batch]
        try:
            result = subprocess.run(["mdls", "-name", ATTR, *chunk],
                                    capture_output=True, text=True, timeout=180).stdout
        except Exception:
            continue
        for segment, path in zip(result.split(ATTR)[1:], chunk):
            names = [labels[n] for n in re.findall(r'"1-(\d+)"', segment) if n in labels]
            if names:
                out[path] = ", ".join(dict.fromkeys(names))
    return out
