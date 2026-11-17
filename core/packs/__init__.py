"""Packs: the domain knowledge the stages read. The engine itself knows nothing about any product,
region or industry.

    available() -> {id: pack}                 every pack: the shipped ones, plus your private ones
    load(deal, config) -> (packs, problems)   the packs a deal uses, in order, validated
    suggest(deal, config) -> [(id, why)]      packs that look relevant to this pack's text
    domains(packs) -> {key: domain}           every domain the product packs declare
    catalogue(packs) -> {key: module}         every product module, with its evidence
    scope_rules(packs) -> [rule]              binding rules (e.g. no OT claims) stages 2 and 4 apply
    regulations(packs) -> [regulation]        from the region and industry packs
    evidence_for(packs, key) -> entry|None    a catalogue entry that can support a rating

Pack layout (packs/<type>/<id>/):
    pack.yaml        id, label, type, signals; for a product: domains, catalogue, licence_metrics
    *.md             the prose the stages quote: where evidence lives, what the pack covers
    checks.yaml      optional: the region's regulations, the industry's typical requirements

Two places are searched, shipped first:
    <repo>/packs/                 what the project publishes
    ~/.bidforge/local-packs/      yours, never committed (BIDFORGE_HOME moves it)

A pack in the private folder with the same id as a shipped one replaces it, so a private copy of a
product catalogue can also correct or extend the published one. Nothing here reads the deal folder or
a customer file: a product pack is knowledge, a deal is content, and only packs live outside git.

A catalogue entry with no `evidence` and no `confirmed` can't support a compliance rating. That is how
rule 3 (never invent SKUs, licence metrics or certifications) is kept mechanically: the pack may list
a module, but until someone sources it, a rating built on it prints as unverified.
"""
from pathlib import Path

import yaml

from core.paths import LOCAL_PACKS, PACKS

TYPES = ("products", "regions", "industries")
KIND = {"products": "product", "regions": "region", "industries": "industry"}


class PackError(RuntimeError):
    pass


def _read(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {} if data is None else data


def _scan(root: Path, out, private):
    """Add every pack under `root`, marking where it came from. Later roots win on the same id."""
    for folder in TYPES:
        base = root / folder
        for d in sorted(base.iterdir()) if base.is_dir() else []:
            if not (d / "pack.yaml").exists():
                continue
            meta = _read(d / "pack.yaml", {})
            pid = meta.get("id") or d.name
            # `checks:` may sit in pack.yaml (the usual place) or in a separate checks.yaml; merge both
            checks = {**(_read(d / "checks.yaml", {}) or {}), **(meta.get("checks") or {})}
            out[pid] = {
                "id": pid, "label": meta.get("label") or pid, "type": meta.get("type") or KIND[folder],
                "folder": folder, "path": str(d), "version": meta.get("version"),
                "signals": [s.lower() for s in meta.get("signals") or []],
                "meta": meta,
                "checks": checks,
                "private": private,
                "prose": {p.name: p.read_text(encoding="utf-8") for p in sorted(d.glob("*.md"))},
            }


def available():
    """{id: pack} for every pack on disk, keyed by its id (folder name unless pack.yaml says otherwise).

    Shipped packs are read first, then your private ones under ~/.bidforge/local-packs/, so a private
    pack with the same id replaces the shipped one rather than colliding with it.
    """
    out = {}
    _scan(PACKS, out, private=False)
    _scan(LOCAL_PACKS, out, private=True)
    return out


def get(pid):
    try:
        return available()[pid]
    except KeyError:
        raise PackError(f"no pack `{pid}` (bid packs list)") from None


def selected(deal):
    return list((deal.bid().get("packs") or []))


def load(deal, config):
    """The packs this deal uses. A named pack that isn't installed is an error, not a silent skip."""
    all_ = available()
    out, problems = [], []
    for pid in selected(deal):
        if pid in all_:
            out.append(all_[pid])
        else:
            problems.append(f"bid.yaml names pack `{pid}`, which isn't installed (bid packs list)")
    if (deal.bid().get("packs_from_stage1") or {}).get("suggested") and not out:
        problems.append("no packs chosen yet (bid packs use <id>)")
    return out, problems


# ---------------------------------------------------------------- what the stages read
def of_type(packs, kind):
    return [p for p in packs if p["type"] == kind]


def domains(packs):
    """Every domain the product packs declare, plus `unassigned` (a requirement that fits no pack domain)."""
    out = {"unassigned": {"label": "Unassigned", "match": [], "pack": None}}
    for p in of_type(packs, "product"):
        for key, dom in ((p["meta"].get("domains")) or {}).items():
            out[key] = dict(dom, pack=p["id"])
    return out


def catalogue(packs):
    """{module key: entry} from every product pack. A key used twice is ambiguous, so it keeps the pack."""
    out = {}
    for p in of_type(packs, "product"):
        for key, mod in ((p["meta"].get("catalogue")) or {}).items():
            out[key] = dict(mod, pack=p["id"], key=key)
    return out


def sourced(entry):
    """Can this catalogue entry support a rating? Only with a source or a named confirmation."""
    return bool(entry.get("evidence") or entry.get("confirmed"))


def scope_rules(packs):
    out = []
    for p in of_type(packs, "product"):
        for n, rule in enumerate((p["meta"].get("scope_rules")) or [], 1):
            out.append(dict(rule, pack=p["id"], id=rule.get("id") or f"{p['id']}-rule-{n}"))
    return out


def licence_metrics(packs):
    out = []
    for p in of_type(packs, "product"):
        for m in (p["meta"].get("licence_metrics")) or []:
            out.append(dict(m, pack=p["id"]))
    return out


def regulations(packs):
    """Region and industry obligations the deal has to be checked against."""
    out = []
    for kind in ("region", "industry"):
        for p in of_type(packs, kind):
            for reg in ((p["checks"].get("regulations")) or []):
                out.append(dict(reg, pack=p["id"], pack_type=p["type"]))
    return out


def typical(packs, kind):
    """Typical requirements / risks / sensitivities an industry pack lists."""
    out = []
    for p in of_type(packs, kind):
        for item in ((p["checks"].get("typical")) or []):
            out.append(dict(item, pack=p["id"]))
    return out


def ai_checks(packs, config):
    """AI-specific checks: the configuration's own list, plus anything a pack adds."""
    out = list((config.get("security") or {}).get("ai_checks") or [])
    for p in packs:
        out += [c for c in ((p["checks"].get("ai_checks")) or []) if c not in out]
    return out


def requirements_rows(packs):
    """The industry pack's requirement themes: prompts, never requirements (they still need a REQ)."""
    return typical(packs, "industry")


# ---------------------------------------------------------------- suggestion
def suggest(deal, config, text=None):
    """[(pack id, why)] from the pack's own words: headings, file names and a sample of the text."""
    from core.intake.run import docs, load_blocks
    all_ = available()
    if text is None:
        blocks = load_blocks(deal).values()
        names = " ".join(d["name"] for d in docs(deal))
        heads = " ".join(b["text"][:120] for b in blocks if b["kind"] == "heading")
        body = " ".join(b["text"][:200] for b in list(blocks)[:400])
        text = f"{names} {heads} {body}".lower()
    else:
        text = text.lower()
    out = []
    for pid, p in all_.items():
        hits = [s for s in p["signals"] if s in text]
        if p["folder"] == "regions" and p["label"].lower() not in text:
            hits = [h for h in hits if h in text]
        if hits:
            out.append((pid, ", ".join(hits[:4])))
    return sorted(out, key=lambda x: -len(x[1].split(",")))


# ---------------------------------------------------------------- validation
def check(deal=None, config=None):
    """(problems, unsourced) — problems are malformed packs the stages can't use; unsourced is a count of
    catalogue entries with nothing behind them. An unsourced entry is not an error: the stage still
    works, it just prints the rating as unverified. It is a to-do list, not a failure."""
    from core.deal.deal import DealError
    problems, unsourced = [], []
    all_ = available()
    if not all_:
        problems.append("no packs installed (packs/products, packs/regions, packs/industries are empty)")
    for pid, p in all_.items():
        meta = p["meta"]
        if not meta.get("label"):
            problems.append(f"{pid}: no `label`")
        if p["folder"] == "products" and not (meta.get("domains") or {}):
            problems.append(f"{pid}: a product pack needs `domains:` (Stage 3 groups scope by domain)")
        for key, mod in ((meta.get("catalogue")) or {}).items():
            if not isinstance(mod, dict):
                problems.append(f"{pid}.catalogue.{key}: expected a mapping with `covers`")
                continue
            if not mod.get("covers"):
                problems.append(f"{pid}.catalogue.{key}: no `covers`, so it can't be matched to a requirement")
            if not sourced(mod):
                unsourced.append(f"{pid}.catalogue.{key}")
        for n, rule in enumerate((meta.get("scope_rules")) or [], 1):
            if not isinstance(rule, dict) or not rule.get("text"):
                problems.append(f"{pid}.scope_rules {n}: expected `text`")
        for n, dom in enumerate(((meta.get("domains")) or {}).items(), 1):
            if not (dom[1] or {}).get("label"):
                problems.append(f"{pid}.domains.{dom[0]}: no `label`")
        for n, reg in enumerate((p["checks"].get("regulations")) or [], 1):
            if not isinstance(reg, dict) or not reg.get("name"):
                problems.append(f"{pid}.checks.regulations {n}: no `name`")
    if deal is not None:
        try:
            _, more = load(deal, config or {})
            problems += more
        except DealError:
            pass
    return problems, unsourced
