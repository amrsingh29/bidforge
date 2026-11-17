"""Which domain a requirement belongs to, and which pack module covers it.

    guess(req, packs) -> domain key         the best match from the pack's `match` words
    module_for(req, packs) -> key|None      a catalogue entry whose `covers` fits the requirement
    split(reqs, packs) -> {domain: [req]}   the requirement set grouped the way Stage 3 works through it

The code makes a first pass so the model starts from a proposal instead of a blank page, and so a
1,000-requirement pack can be worked through a domain at a time. The model can move a requirement to
another domain; it can't invent one.
"""
import re

from core import packs as P


def _words(text):
    return set(re.findall(r"[a-z0-9][a-z0-9+#.-]{2,}", (text or "").lower()))


def _hits(terms, text_words):
    """How many of a pack's match terms appear. A multi-word term needs all its words present."""
    n = 0
    for t in terms or []:
        parts = _words(t)
        if parts and parts <= text_words:
            n += 1
    return n


def guess(req, packs):
    doms = P.domains(packs)
    text = f"{req.get('text', '')} {' '.join(req.get('buyer_ref') or [])}"
    w = _words(text)
    best, best_n = None, 0
    for key, dom in doms.items():
        if key == "unassigned":
            continue
        n = _hits(dom.get("match"), w)
        if n > best_n:
            best, best_n = key, n
    return best or "unassigned"


def module_for(req, packs):
    text = _words(req.get("text", ""))
    best, best_n = None, 0
    for key, entry in P.catalogue(packs).items():
        n = _hits(str(entry.get("covers", "")).split(","), text)
        if n > best_n:
            best, best_n = key, n
    return best


def split(reqs, packs):
    """Groups requirement dicts by domain, in the pack's declared order, unassigned last."""
    doms = list(P.domains(packs))
    out = {k: [] for k in doms}
    for r in reqs:
        out[guess(r, packs)].append(r)
    return {k: v for k, v in out.items() if v}
