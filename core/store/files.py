"""Safe JSON files for deal data. Deals usually live in a synced folder (OneDrive, SharePoint, iCloud), where a
file rewritten seconds apart can be read back stale or half-written. So every write goes to a temporary
file first and replaces the old one in a single step, and data that grows chunk by chunk is kept one
file per chunk: a stale read of one file can then never wipe out another chunk's work.

    read(path, default) · write(path, data)
"""
import json, os, tempfile
from pathlib import Path


def read(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
