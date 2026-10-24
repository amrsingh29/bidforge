"""Intake: parse the pack, mark candidates, cut the work into chunks for the model pass.

    intake(deal, config, force=False) -> summary dict
    load_blocks(deal) -> {block id: block}
    docs(deal) -> [doc record]
    chunks(deal) -> [chunk]  /  save_chunks(deal, chunks)

Files on disk (data/):
    docs.json     one record per pack file: kind, size, fingerprint, stats, what couldn't be read
    blocks.json   every block with its id (B-0001…), location and candidate reason
    chunks.json   the model's work packets (K-01…), each pending or done
"""
import hashlib
from pathlib import Path

from core.intake import candidates
from core.intake.parse import parse
from core.store import files


class IntakeError(RuntimeError):
    pass


def _p(deal, name):
    return deal.path / "data" / name


def _read(deal, name, default):
    return files.read(_p(deal, name), default)


def _write(deal, name, data):
    files.write(_p(deal, name), data)


def docs(deal):
    return _read(deal, "docs.json", [])


def load_blocks(deal):
    return {b["id"]: b for b in _read(deal, "blocks.json", [])}


def chunks(deal):
    """The chunks, with their status worked out from what is on disk: a chunk is done when it had nothing
    to account for, or its requirements file exists and it hasn't been reopened by --remark. (Status
    isn't stored in chunks.json, so a stale copy of that file can't undo finished work.)"""
    out = _read(deal, "chunks.json", [])
    for c in out:
        saved = (_p(deal, "requirements") / f"{c['id']}.json").exists()
        c["status"] = "done" if c.get("auto") or (saved and not c.get("reopened")) else "pending"
    return out


def save_chunks(deal, ch):
    _write(deal, "chunks.json", ch)


def fingerprint(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()[:16]


def intake(deal, config, force=False):
    files = [f["path"] for f in deal.pack()]
    if not files:
        raise IntakeError("the pack has no files (bid pack add FILES)")
    prints = {f: fingerprint(f) if Path(f).exists() else None for f in files}
    before = {d["path"]: d["fingerprint"] for d in docs(deal)}
    started = any(c["status"] == "done" for c in chunks(deal))
    if before and before == prints and not force:
        return {"unchanged": True}
    if started and not force:
        raise IntakeError("extraction has started and the pack changed: re-running intake would discard it. "
                          "Use --force to start extraction again (addendum handling comes in Phase 4).")
    parsed = [parse(f) for f in files]
    # buyer compliance matrices go last, so their rows can be linked to requirements already extracted
    for d in parsed:
        candidates.mark(d.blocks, config)
    is_matrix = lambda d: any(b.get("cand") == "matrix row" for b in d.blocks)
    parsed.sort(key=lambda d: (is_matrix(d), files.index(d.path)))
    blocks, records, n = [], [], 0
    for d in parsed:
        for b in d.blocks:
            n += 1
            b["id"] = f"B-{n:04d}"
            blocks.append(b)
        records.append({"name": d.name, "path": d.path, "kind": d.kind, "fingerprint": prints[d.path],
                        "size": Path(d.path).stat().st_size if Path(d.path).exists() else None,
                        "stats": d.stats, "unread": d.unread, "blocks": len(d.blocks),
                        "candidates": sum(1 for b in d.blocks if b.get("cand")), "matrix": is_matrix(d)})
    _write(deal, "docs.json", records)
    _write(deal, "blocks.json", blocks)
    save_chunks(deal, cut(blocks, config))
    if force:                                     # a fresh extraction: earlier chunk results no longer fit
        for stale in [*_p(deal, "requirements").glob("K-*.json"), _p(deal, "spotcheck.json")]:
            if stale.exists():
                stale.unlink()
    return {"docs": records, "blocks": len(blocks), "candidates": sum(1 for b in blocks if b.get("cand")),
            "chunks": len(chunks(deal))}


def remark(deal, config):
    """Mark candidates again on the existing blocks (after a change to candidate_words, or a better code
    pass) without re-parsing: block IDs, requirements and finished chunks stay. A finished chunk that
    now has a candidate nobody accounted for goes back to pending."""
    from core.store import requirements as R
    blocks = _read(deal, "blocks.json", [])
    if not blocks:
        raise IntakeError("no intake yet (bid intake)")
    candidates.mark(blocks, config)
    _write(deal, "blocks.json", blocks)
    by_id = {b["id"]: b for b in blocks}
    store = R.load(deal)
    seen = {b for r in store["items"] for b in r["blocks"]} | {b for d in store["dismissed"] for b in d["blocks"]}
    reopened = []
    ch = chunks(deal)
    for c in ch:
        c["candidates"] = sum(1 for i in c["blocks"] if by_id[i].get("cand"))
        open_ = [i for i in c["blocks"] if by_id[i].get("cand") and i not in seen]
        if open_ and c["status"] == "done":
            c["auto"], c["reopened"] = False, True
            reopened.append(c["id"])
        elif not open_ and c["status"] == "pending" and not any(r["chunk"] == c["id"] for r in store["items"]):
            c["auto"] = True                          # nothing left in it to account for
    save_chunks(deal, ch)
    return {"candidates": sum(1 for b in blocks if b.get("cand")), "reopened": reopened}


def cut(blocks, config):
    """Chunks per document, at most max_blocks / max_chars, cut at a heading where possible.
    Chunks with no candidate at all are marked done straight away (nothing to account for)."""
    lim = config["requirements"]["chunk"]
    out, cur, size = [], [], 0

    def close():
        nonlocal cur, size
        if cur:
            has = any(b.get("cand") for b in cur)
            out.append({"id": f"K-{len(out) + 1:02d}", "doc": cur[0]["doc"], "blocks": [b["id"] for b in cur],
                        "candidates": sum(1 for b in cur if b.get("cand")),
                        "status": "pending" if has else "done", "auto": not has})
        cur, size = [], 0

    for b in blocks:
        if cur and (b["doc"] != cur[0]["doc"]
                    or len(cur) >= lim["max_blocks"] or size + len(b["text"]) > lim["max_chars"]
                    or (b["kind"] == "heading" and len(cur) >= lim["max_blocks"] * 0.6)):
            close()
        cur.append(b)
        size += len(b["text"])
    close()
    return out
