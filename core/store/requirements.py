"""Requirements: what the model pass records for each chunk, checked against the source before it's kept.

    render_chunk(deal, chunk_id) -> text the model reads (blocks, candidates, context, the JSON to write)
    save_chunk(deal, chunk_id, data, config) -> (saved requirements, problems)   nothing is kept if problems
    load(deal) -> {"items": [...], "dismissed": [...]}
    cite(block) -> "main-rfp.docx, §5.1.2 ¶3"

A requirement:  {id: REQ-001, blocks: [B-…], text, type, obligation, buyer_ref, restates: [REQ-…],
                 section, chunk, via: candidate|added}
The checks are the fixed rules made mechanical: every candidate accounted for, every requirement
cites blocks of its own chunk, its wording is traceable to those blocks, and types and obligations
come from the configuration.
"""
import json, re

from core.intake.candidates import ID_LIKE as _ID
from core.intake.run import chunks, load_blocks, save_chunks
from core.store import files

FAITHFUL = 0.6            # share of a requirement's content words that must appear in its source blocks
WORD = re.compile(r"[a-z0-9][a-z0-9'’-]{3,}")


class StoreError(RuntimeError):
    pass


def _dir(deal):
    return deal.path / "data" / "requirements"


def load(deal):
    """Every chunk's requirements and dismissals, merged. Duplicate IDs mean a lost update and are refused."""
    d = _dir(deal)
    _migrate(deal)
    items, dismissed = [], []
    for f in sorted(d.glob("K-*.json")) if d.is_dir() else []:
        part = files.read(f, {})
        items += part.get("items", [])
        dismissed += part.get("dismissed", [])
    seen = {}
    for r in items:
        if r["id"] in seen:
            raise StoreError(f"{r['id']} is used by chunks {seen[r['id']]} and {r['chunk']}: re-save one of them "
                             "(bid extract save) to give it new IDs")
        seen[r["id"]] = r["chunk"]
    return {"items": sorted(items, key=lambda r: int(r["id"][4:])), "dismissed": dismissed}


def _save_chunk(deal, chunk_id, items, dismissed):
    files.write(_dir(deal) / f"{chunk_id}.json", {"chunk": chunk_id, "items": items, "dismissed": dismissed})


def _migrate(deal):
    """Deals from before per-chunk files kept everything in one requirements.json."""
    old = deal.path / "data" / "requirements.json"
    if not old.exists() or _dir(deal).is_dir():
        return
    data = files.read(old, {"items": [], "dismissed": []})
    for c in sorted({r["chunk"] for r in data["items"]} | {d["chunk"] for d in data["dismissed"]}):
        _save_chunk(deal, c, [r for r in data["items"] if r["chunk"] == c], [d for d in data["dismissed"] if d["chunk"] == c])
    old.rename(old.with_suffix(".json.migrated"))


def cite(b):
    name = b["doc"].rsplit(".", 1)[0]
    return f"{name}, {b['loc']}"


def words(text):
    return {w[:6] for w in WORD.findall(text.lower())}


def faithful(text, sources):
    want = words(text)
    if not want:
        return True
    have = set().union(*(words(s) for s in sources)) if sources else set()
    return len(want & have) / len(want) >= FAITHFUL


# ---------------------------------------------------------------- what the model reads
def render_chunk(deal, chunk_id, config):
    ch = _chunk(deal, chunk_id)
    blocks = load_blocks(deal)
    req = config["requirements"]
    lines = [f"# Chunk {ch['id']} of {len(chunks(deal))} — {ch['doc']} ({len(ch['blocks'])} blocks, "
             f"{ch['candidates']} candidates)", ""]
    heading, empty = None, []

    def flush():
        if empty:
            lines.append(f"{empty[0]}..{empty[-1]} [ctx] {len(empty)} empty template row(s)" if len(empty) > 1
                         else f"{empty[0]} [ctx] {blocks[empty[0]]['loc']}: {blocks[empty[0]]['text']}")
            empty.clear()

    for bid in ch["blocks"]:
        b = blocks[bid]
        if not b.get("cand") and b["kind"] == "row" and all(_ID.match(c) for c in b.get("cells", []) if c):
            empty.append(bid)                       # e.g. a Q&A log's numbered blank rows: one line, not forty
            continue
        flush()
        if b.get("heading") != heading and b["kind"] != "heading":
            heading = b.get("heading")
            lines.append(f"  (under: {heading})")
        mark = f"CAND:{b['cand']}" if b.get("cand") else "ctx"
        if b["kind"] == "heading":
            heading = b.get("heading")
            lines.append(f"{bid} [heading{', CAND:' + b['cand'] if b.get('cand') else ''}] {b['loc']}: {b['text']}")
        else:
            lines.append(f"{bid} [{mark}] {b['loc']}: {b['text']}")
    flush()
    matrix = [blocks[i] for i in ch["blocks"] if blocks[i].get("matrix")]
    if matrix:
        secs = {m["matrix"].get("section_ref") for m in matrix} - {None}
        have = [r for r in load(deal)["items"] if r.get("section") in secs or _parent_in(r.get("section"), secs)]
        lines += ["", "## Requirements already extracted from the RFP body for the sections this chunk refers to",
                  "(for `restates`: which of these each buyer matrix row restates)"]
        doc = lambda r: blocks[r["blocks"][0]]["doc"].rsplit(".", 1)[0]
        lines += [f"{r['id']} [{doc(r)}] §{r.get('section')}: {r['text']}" for r in have] or ["(none)"]
    lines += ["", "## Write this JSON", "```json", json.dumps({
        "requirements": [{"blocks": ["B-…"], "text": "short and faithful to the source wording",
                          "type": "|".join(req["types"]), "obligation": "|".join(req["obligations"]),
                          "restates": ["REQ-… (buyer matrix rows only, else omit)"]}],
        "dismissed": [{"blocks": ["B-…", "B-0100..B-0150 (a range)"], "reason": "why these candidates are not requirements"}]}, indent=1), "```"]
    return "\n".join(lines)


def expand(ids, order):
    """"B-0100..B-0150" -> every candidate block of the chunk in that range (for dismissing a run of
    pricing lines in one go); plain IDs pass through."""
    out = []
    for i in ids:
        if ".." in i:
            a, b = i.split("..")
            if a in order and b in order:
                out += order[order.index(a):order.index(b) + 1]
                continue
        out.append(i)
    return out


def _parent_in(section, secs):
    return bool(section) and any(section.startswith(s + ".") for s in secs)


def _chunk(deal, chunk_id):
    for c in chunks(deal):
        if c["id"].lower() == chunk_id.lower():
            return c
    raise KeyError(f"no chunk {chunk_id}")


# ---------------------------------------------------------------- save, with the checks
def save_chunk(deal, chunk_id, data, config):
    ch = _chunk(deal, chunk_id)
    blocks = load_blocks(deal)
    own = set(ch["blocks"])
    req = config["requirements"]
    store = load(deal)
    known_ids = {r["id"] for r in store["items"]}
    problems, cited, dismissed = [], set(), set()
    items = data.get("requirements") or []
    if not isinstance(items, list):
        return [], ["`requirements` must be a list"]
    for n, r in enumerate(items, 1):
        where = f"requirement {n}"
        bids = r.get("blocks") or []
        if not bids:
            problems.append(f"{where}: no `blocks` (every requirement cites its source)")
            continue
        outside = [b for b in bids if b not in own]
        if outside:
            problems.append(f"{where}: cites {', '.join(outside)}, not in chunk {ch['id']}")
            continue
        if not (r.get("text") or "").strip():
            problems.append(f"{where}: empty `text`")
        elif not faithful(r["text"], [blocks[b]["text"] for b in bids]):
            problems.append(f"{where}: wording isn't traceable to {', '.join(bids)} "
                            "(keep the buyer's words; don't add what the source doesn't say)")
        if r.get("type") not in req["types"]:
            problems.append(f"{where}: type {r.get('type')!r} is not one of {', '.join(req['types'])}")
        if r.get("obligation") not in req["obligations"]:
            problems.append(f"{where}: obligation {r.get('obligation')!r} is not one of {', '.join(req['obligations'])}")
        bad = [x for x in r.get("restates") or [] if x not in known_ids]
        if bad:
            problems.append(f"{where}: restates unknown {', '.join(bad)}")
        cited.update(bids)
    for d in data.get("dismissed") or []:
        d["blocks"] = expand(d.get("blocks") or ([d["block"]] if d.get("block") else []), ch["blocks"])
    for n, d in enumerate(data.get("dismissed") or [], 1):
        bids = d["blocks"]
        if not (d.get("reason") or "").strip():
            problems.append(f"dismissal {n}: give a `reason`")
        outside = [b for b in bids if b not in own]
        if outside:
            problems.append(f"dismissal {n}: {', '.join(outside)} not in chunk {ch['id']}")
        dismissed.update(bids)
    both = cited & dismissed
    if both:
        problems.append(f"{', '.join(sorted(both))}: both cited and dismissed")
    missing = [b for b in ch["blocks"] if blocks[b].get("cand") and b not in cited and b not in dismissed]
    if missing:
        problems.append(f"{len(missing)} candidate(s) not accounted for: {', '.join(missing)} "
                        "(cite each in a requirement or dismiss it with a reason)")
    if problems:
        return [], problems

    previous = [r for r in store["items"] if r["chunk"] == ch["id"]]
    next_n = max([int(r["id"][4:]) for r in store["items"]] + [0]) + 1
    saved = []
    for r in items:
        first = blocks[r["blocks"][0]]
        keep = next((p for p in previous if p["blocks"][0] == r["blocks"][0] and faithful(r["text"], [p["text"]])), None)
        if keep:
            previous.remove(keep)
            rid = keep["id"]
        else:
            rid, next_n = f"REQ-{next_n:03d}", next_n + 1
        m = first.get("matrix") or {}
        saved.append({"id": rid, "blocks": r["blocks"], "text": r["text"].strip(), "type": r["type"],
                      "obligation": r["obligation"], "section": m.get("section_ref") or first.get("section"),
                      "buyer_ref": m.get("ref"), "restates": r.get("restates") or [],
                      "chunk": ch["id"], "via": "candidate" if any(blocks[b].get("cand") for b in r["blocks"]) else "added"})
    _save_chunk(deal, ch["id"], saved, [{"blocks": d["blocks"], "reason": d["reason"].strip(), "chunk": ch["id"]}
                                        for d in data.get("dismissed") or []])
    if ch.get("reopened"):
        all_chunks = chunks(deal)
        for c in all_chunks:
            if c["id"] == ch["id"]:
                c["reopened"] = False
        save_chunks(deal, all_chunks)
    return saved, []
