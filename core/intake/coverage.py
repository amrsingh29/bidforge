"""Coverage report and spot-check: the two things that say whether extraction can be trusted.

    report(deal) -> dict    per document: blocks, candidates, requirements, dismissed, open chunks,
                            what couldn't be read; plus how the buyer's own compliance matrix lines up
    spot_sample(deal, n) -> [requirement]   a fixed, varied sample to check against the source
"""
import random
from collections import Counter

from core.intake.run import chunks, docs, load_blocks
from core.store import requirements as R


def report(deal):
    blocks, store, ch = load_blocks(deal), R.load(deal), chunks(deal)
    cited = {b for r in store["items"] for b in r["blocks"]}
    dismissed = {b for d in store["dismissed"] for b in d["blocks"]}
    per_doc = []
    for d in docs(deal):
        mine = [b for b in blocks.values() if b["doc"] == d["name"]]
        cands = [b["id"] for b in mine if b.get("cand")]
        reqs = [r for r in store["items"] if blocks[r["blocks"][0]]["doc"] == d["name"]]
        per_doc.append({"doc": d["name"], "kind": d["kind"], "blocks": len(mine), "candidates": len(cands),
                        "requirements": len(reqs), "dismissed": sum(1 for c in cands if c in dismissed),
                        "open": sum(1 for c in cands if c not in cited and c not in dismissed),
                        "chunks_open": sum(1 for c in ch if c["doc"] == d["name"] and c["status"] != "done"),
                        "unread": d["unread"], "hidden_sheets": d["stats"].get("hidden_sheets") or [],
                        "matrix": d["matrix"]})
    rows = [r for r in store["items"] if r.get("buyer_ref")]
    body = [r for r in store["items"] if not r.get("buyer_ref")]
    restated = {x for r in rows for x in r["restates"]}
    linked = [r for r in rows if r["restates"]]
    mismatch = []
    by_id = {r["id"]: r for r in store["items"]}
    for r in linked:
        for x in r["restates"]:
            s, t = r.get("section"), by_id[x].get("section")
            if s and t and not (t == s or t.startswith(s + ".") or s.startswith(t + ".")):
                mismatch.append((r["id"], x, s, t))
    matrix = None
    if rows:
        matrix = {"rows": len(rows), "linked": len(linked), "share": len(linked) / len(rows),
                  "unlinked": [r["id"] for r in rows if not r["restates"]],
                  "unlinked_mandatory": [r["id"] for r in rows if not r["restates"] and r["obligation"] in ("mandatory", "disqualifier")],
                  "body_not_in_matrix": [r["id"] for r in body if r["id"] not in restated],
                  "section_mismatch": mismatch}
    total = {k: sum(d[k] for d in per_doc) for k in ("blocks", "candidates", "requirements", "dismissed", "open", "chunks_open")}
    return {"docs": per_doc, "total": total, "matrix": matrix,
            "obligations": dict(Counter(r["obligation"] for r in store["items"])),
            "types": dict(Counter(r["type"] for r in store["items"])),
            "added": sum(1 for r in store["items"] if r["via"] == "added"),
            "complete": total["open"] == 0 and total["chunks_open"] == 0 and total["candidates"] > 0}


def spot_sample(deal, n):
    """Varied on purpose: mandatory items, every document, spreadsheet rows, requirements the model
    added beyond the code pass, and dismissals (to catch a requirement thrown away)."""
    store = R.load(deal)
    blocks = load_blocks(deal)
    rng = random.Random(deal.slug)                 # same sample every time for the same deal
    items = store["items"]
    picks, seen = [], set()

    def take(pool, k):
        pool = [x for x in pool if x["id"] not in seen]
        for x in rng.sample(pool, min(k, len(pool))):
            picks.append(x); seen.add(x["id"])

    take([r for r in items if r["obligation"] in ("mandatory", "disqualifier")], max(2, n // 4))
    take([r for r in items if r["via"] == "added"], 2)
    take([r for r in items if "sheet" in blocks[r["blocks"][0]]], 2)
    for d in sorted({blocks[r["blocks"][0]]["doc"] for r in items}):
        if len(picks) >= n - 2:
            break
        take([r for r in items if blocks[r["blocks"][0]]["doc"] == d], 1)
    take(items, max(0, n - 2 - len(picks)))
    dismissals = [dict(d, id=f"dismissed:{d['blocks'][0]}") for d in store["dismissed"]]
    take(dismissals, 2)
    return picks
