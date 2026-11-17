"""Evidence lookup: what we can actually show for a claim, in the order the plan ranks the sources.

    1. past RFP responses (a Loopio library export works as one)
    2. product documentation
    3. the user's confirmation (recorded in data/evidence.json)

    library() -> {id: entry}                   every document in the local evidence library
    lookup(text, deal) -> entry|None           the best match for a topic, or None
    record(deal, key, text, by="user")         a confirmation, kept with the deal
    verify(deal, citation) -> (ok, why)        does this citation point at something real?

The library is plain files under ~/.bidforge/evidence/ (BIDFORGE_EVIDENCE overrides): .md, .txt and
.json, each with a one-line topic header. Nothing here calls out to a service: an RFP pack and a
customer's past answers stay on disk.

Rule 9 depends on this module being honest. When there is nothing to show, lookup returns None and the
caller prints **unverified** — it never falls back to "the pack says we do this".
"""
import json, os, re
from pathlib import Path

from core.paths import HOME
from core.store import files

LIBRARY = Path(os.environ.get("BIDFORGE_EVIDENCE", HOME / "evidence")).expanduser()
WORD = re.compile(r"[a-z0-9][a-z0-9+#.-]{3,}")
STOP = {"that", "with", "from", "this", "shall", "must", "should", "system", "platform", "solution",
        "support", "supports", "provide", "provides", "required", "requirement", "within", "including"}


def _terms(text):
    return {w[:7] for w in WORD.findall((text or "").lower()) if w not in STOP}


def library():
    """{id: {source, topic, text, path}} for every readable file in the library."""
    out = {}
    if not LIBRARY.is_dir():
        return out
    for p in sorted(LIBRARY.rglob("*")):
        if p.suffix.lower() not in (".md", ".txt", ".json") or not p.is_file():
            continue
        try:
            raw = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        topic, text = p.stem, raw
        if p.suffix.lower() == ".json":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                topic = data.get("topic") or topic
                text = data.get("text") or json.dumps(data)[:2000]
        else:
            first = raw.strip().splitlines()[0] if raw.strip() else ""
            if first.startswith("#"):
                topic = first.lstrip("# ").strip() or topic
        out[str(p.relative_to(LIBRARY))] = {"source": str(p), "topic": topic, "text": text}
    return out


def _score(want, text):
    have = _terms(text)
    return len(want & have) / len(want) if want else 0.0


def lookup(text, deal=None, threshold=0.5):
    """The best evidence for a topic: the library first, then a confirmation recorded for this deal.

    Returns {"kind": "library"|"confirmation", "source", "topic", "snippet", "score"} or None.
    """
    want = _terms(text)
    if not want:
        return None
    best, best_score = None, threshold
    for eid, e in library().items():
        s = _score(want, f"{e['topic']} {e['text']}")
        if s > best_score:
            best, best_score = {"kind": "library", "id": eid, "source": e["source"], "topic": e["topic"],
                                "snippet": _snippet(e["text"], want), "score": round(s, 2)}, s
    for key, c in confirmations(deal).items():
        s = _score(want, f"{key} {c['text']}")
        if s > best_score:
            best, best_score = {"kind": "confirmation", "id": key, "source": f"confirmed by {c['by']}, {c['date']}",
                                "topic": key, "snippet": c["text"], "score": round(s, 2)}, s
    return best


def _snippet(text, want, width=240):
    low = text.lower()
    hits = [low.find(w) for w in want if low.find(w) >= 0]
    start = max(0, (min(hits) if hits else 0) - width // 3)
    return " ".join(text[start:start + width].split())


# ---------------------------------------------------------------- confirmations, per deal
def _path(deal):
    return deal.path / "data" / "evidence.json"


def confirmations(deal):
    return files.read(_path(deal), {}) if deal is not None else {}


def record(deal, key, text, by="user"):
    """A confirmation the user gave. Kept with the deal, never presented as a document."""
    import datetime as dt
    data = confirmations(deal)
    if (text or "").strip():
        data[key] = {"text": text.strip(), "by": by, "date": f"{dt.date.today():%Y-%m-%d}"}
    else:
        data.pop(key, None)
    files.write(_path(deal), data)
    return data


def verify(deal, citation, blocks=None):
    """Resolve a citation. (exists, verified, why).

    `exists` is whether the thing cited is real — a block, a requirement, a library file, a recorded
    confirmation, a catalogue entry. A mistake here is worth refusing: the model has cited something
    that isn't there.

    `verified` is whether it actually supports a claim. A catalogue entry with no `evidence` exists but
    verifies nothing, so the rating prints **unverified** rather than being refused — that is the honest
    middle ground the pack is built around.

    Accepts a block id, a requirement id, a library id, `confirm:KEY`, or a pack catalogue key.
    """
    from core.store import requirements as R
    cite = (citation or "").strip()
    if not cite:
        return False, False, "empty citation"
    if cite.startswith("confirm:"):
        ok = cite[8:] in confirmations(deal)
        return ok, ok, "" if ok else "not confirmed by the user"
    if cite.startswith("pack:"):
        from core import packs
        key = cite[5:]
        entry = packs.catalogue(packs.load(deal, {})[0] if deal is not None else []).get(key)
        if entry is None:
            return False, False, f"no catalogue entry `{key}`"
        return True, bool(packs.sourced(entry)), ""
    if blocks is not None and cite in blocks:
        return True, True, ""
    if re.fullmatch(r"REQ-\d+", cite):
        ids = {r["id"] for r in R.load(deal)["items"]} if deal is not None else set()
        return (cite in ids), (cite in ids), "no such requirement" if cite not in ids else ""
    if cite in library():
        return True, True, ""
    return False, False, "not a block, requirement, confirmation, catalogue entry or library file"
