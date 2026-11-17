"""Stage 3 — Scope & requirements: the compliance matrix.

    brief(deal, config, domain=None) -> text    one domain (or the scope overview and the domain list),
                                                the requirements to rate, the pack's modules, the JSON to write
    save(deal, data, config) -> (path, problems)  merges one domain's ratings; nothing is kept if problems
    matrix(deal, config) -> dict                the whole matrix: per-domain counts, gaps, unverified
    render(deal, config) -> path                stages/stage-3.md

Stage 3 works one domain at a time, because a 1,000-line matrix doesn't survive a single model call and
an incomplete matrix is worse than an honest partial one. Each `save` merges that domain's ratings into
data/matrix.json; `render` is only allowed once every requirement has a rating.

What the code enforces, in the language of the fixed rules:
  - every requirement in the pack is either rated or explicitly marked unassessed — nothing is dropped (rule 5)
  - a rating must be a configured level, and its evidence must verify (rule 9)
  - a rating resting on a pack catalogue entry with no source prints as unverified, whatever the level
  - a rating with `gap: true` must say what fails, because Stage 4 needs the mitigation (rule 3)
  - scope rules from the product pack are applied: OT scope can't be rated as complying
"""
import datetime as dt

from core import evidence, packs as P
from core.intake.run import load_blocks
from core.stages import domain as D
from core.store import files, registers, state
from core.store import requirements as R


def levels(config):
    return {k: v for k, v in ((config.get("compliance") or {}).get("levels") or {}).items()
            if isinstance(v, dict) and v.get("enabled", True)}


def _matrix_path(deal):
    return deal.path / "data" / "matrix.json"


def load(deal):
    return files.read(_matrix_path(deal), {"domains": {}, "scope": None, "version": 0})


def placement(deal, config):
    """{req id: domain} — the code's guess, overridden by wherever a rating actually put it.

    Stage 3 is worked domain by domain, and the guess will be wrong sometimes (a Q&A row about data
    residency is not obviously "platform"). Rather than argue with the model, the rating's own domain
    becomes the placement, so a moved requirement is neither rated twice nor reported as missing.
    """
    packs, _ = P.load(deal, config)
    reqs = R.load(deal)["items"]
    guess = {r["id"]: D.guess(r, packs) for r in reqs}
    for dom, d in (load(deal).get("domains") or {}).items():
        for rid in (d.get("ratings") or {}):
            if rid in guess:
                guess[rid] = dom
    return guess


def grouped(deal, config):
    """{domain: [requirement, ...]} in the pack's order, using the placement, not just the guess."""
    packs, _ = P.load(deal, config)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    place = placement(deal, config)
    out = {}
    for rid, req in reqs.items():
        out.setdefault(place[rid], []).append(req)
    order = list(P.domains(packs))
    return {k: out[k] for k in sorted(out, key=lambda k: (order.index(k) if k in order else 99, k))}


# ---------------------------------------------------------------- what the model reads
def brief(deal, config, domain=None):
    packs, pack_problems = P.load(deal, config)
    if pack_problems:
        return "# Stage 3 brief\n\n" + "\n".join(f"✗ {p}" for p in pack_problems) + \
               "\n\nFix that first: `bid packs use <id>` (bid packs list)."
    blocks = load_blocks(deal)
    reqs = R.load(deal)["items"]
    mat = load(deal)
    lv = levels(config)
    groups = grouped(deal, config)
    L = ["# Stage 3 brief — scope & requirements", ""]
    if domain is None:
        L += ["## Scope overview (write this first: `bid stage3 scope S.json`)", "",
              "Domains the product pack declares, with how many requirements the code put in each. "
              "Move a requirement if the guess is wrong; a domain can be added only as a scope note.",
              "", "| Domain | Pack | Requirements |", "|---|---|---|"]
        doms = P.domains(packs)
        for key, rs in groups.items():
            L.append(f"| {key} — {doms.get(key, {}).get('label', key)} | {doms.get(key, {}).get('pack') or '—'} "
                     f"| {len(rs)} |")
        L += ["", f"**{len(reqs)} requirements** in total, {len(groups)} domains. Then rate each domain: "
                  "`bid stage3 brief <domain>`.", "", "## Write this JSON for the scope", "```json",
              _json(SCOPE_TEMPLATE(packs)), "```", "", "## Packs in use"]
        for p in packs:
            L.append(f"- {p['id']} ({p['type']}) {p['label']} {p['version'] or ''}".rstrip())
        return "\n".join(L)

    key = domain if domain in groups else None
    if key is None:
        return (f"# Stage 3 — {domain}\n\nNo requirements are grouped under `{domain}`. "
                f"Domains with work: {', '.join(groups) or 'none'}.")
    dom = P.domains(packs).get(domain, {})
    done = (mat["domains"].get(domain) or {}).get("ratings") or {}
    todo = [r for r in groups[key] if r["id"] not in done] if not (mat["domains"].get(domain) or {}).get("done") else []
    L += [f"## Domain `{domain}` — {dom.get('label', domain)}" + (f" (pack {dom.get('pack')})" if dom.get("pack") else ""),
          "", f"{len(groups[key])} requirement(s) in this domain, {len(done)} already rated, "
              f"{len(todo) if todo is not None else 0} to do.", ""]
    if (mat["domains"].get(domain) or {}).get("done"):
        L += ["This domain is already rated. Re-running replaces its ratings.", ""]

    scope = (mat.get("scope") or {}).get("domains") or {}
    if scope.get(domain):
        L += [f"**Scope note on file:** {scope[domain].get('note', '')}", ""]

    L += ["## Requirements to rate", ""]
    for r in (todo or groups[key]):
        cite = R.cite(blocks[r["blocks"][0]]) if r["blocks"] and r["blocks"][0] in blocks else "—"
        flag = {"disqualifier": "[DISQUALIFIER] ", "mandatory": "[MANDATORY] "}.get(r["obligation"], "")
        L.append(f"{r['id']} [{r['type']}] {flag}{r['text']}  ({cite})")
        mod = D.module_for(r, packs)
        if mod:
            entry = P.catalogue(packs).get(mod) or {}
            src = "sourced" if P.sourced(entry) else "NO SOURCE YET — a rating resting on it prints unverified"
            L.append(f"    code suggestion: module `{mod}` ({src})")

    L += ["", "## Modules in this product pack", "",
          "| Module | Covers | Evidence |", "|---|---|---|"]
    for mk, entry in P.catalogue(packs).items():
        L.append(f"| {mk} | {entry.get('covers', '')} | {entry.get('evidence') or entry.get('confirmed') or '**none — unverified**'} |")

    rules = P.scope_rules(packs)
    if rules:
        L += ["", "## Scope rules that bind these ratings"]
        L += [f"- **{r['id']}**: {' '.join(str(r['text']).split())}" for r in rules]

    L += ["", "## Levels", ""]
    L += [f"- `{k}` — {v.get('label')}" + (" **(counts as a gap)**" if v.get("gap") else "")
          + (f": {v.get('note')}" if v.get("note") else "") for k, v in lv.items()]

    ev = _evidence_hints(deal, todo or groups[key])
    if ev:
        L += ["", "## What the evidence library already has for these requirements",
              "(a starting point, not a verdict — check it actually answers the requirement)", ""]
        L += ev

    L += ["", "## Write this JSON for the domain", "```json", _json(DOMAIN_TEMPLATE(domain, todo or groups[key], config)), "```"]
    return "\n".join(L)


def _json(x):
    import json
    return json.dumps(x, indent=1, ensure_ascii=False)


def _evidence_hints(deal, reqs):
    """Only hints. A looser threshold than `bid evidence find` on purpose: a near miss is worth seeing,
    and anything actually cited is verified at save."""
    out = []
    for r in reqs[:60]:
        e = evidence.lookup(r["text"], deal, threshold=0.35)
        if e:
            out.append(f"- {r['id']} → {e['kind']} {e['id']} ({e['score']}): {e['snippet'][:150]}")
    return out


def SCOPE_TEMPLATE(packs):
    return {
        "domains": {k: {"note": "what the buyer wants in this domain, in one or two lines", "label": ""}
                    for k in list(P.domains(packs))[:3]},
        "out_of_scope": [{"text": "explicitly excluded by the buyer, or excluded by a scope rule", "sources": ["B-…", "REQ-…"]}],
        "statistics": {"note": "optional: anything worth counting for the buyer (volumes, sites, users)"},
    }


def DOMAIN_TEMPLATE(domain, reqs, config):
    lv = list(levels(config))
    return {
        "domain": domain,
        "ratings": [{"req": r["id"], "level": "|".join(lv), "module": "pack module key, or empty",
                     "evidence": [{"kind": "|".join((config["compliance"].get("evidence_kinds") or {})), "cite": "…"}],
                     "what_fails": "required only when the level counts as a gap",
                     "note": ""} for r in reqs[:3]],
        "unknowns": [{"text": "", "sources": ["REQ-…"]}],
        "confirms": [{"text": "", "role": "", "question": ""}],
    }


# ---------------------------------------------------------------- save
def save(deal, data, config):
    """Save one domain's ratings (or, with `domains:` and no `ratings:`, the scope overview)."""
    packs, pack_problems = P.load(deal, config)
    problems = list(pack_problems)
    blocks = load_blocks(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    lv = levels(config)
    kinds = (config["compliance"].get("evidence_kinds") or {})
    mat = load(deal)
    st = state.load(deal)
    if not st["stages"].get("stage2", {}).get("gate_passed"):
        problems.append("the Stage 2 gate hasn't been passed (bid gate pass stage2)")

    if data.get("ratings") is not None:
        dom = data.get("domain")
        groups = grouped(deal, config)
        if dom not in P.domains(packs):
            problems.append(f"domain {dom!r} isn't declared by any product pack (bid packs list)")
        # A requirement can be rated in a domain the code didn't guess: the guess is a proposal and the
        # rating is the decision. What isn't allowed is rating the same requirement in two domains.
        elsewhere = {rid for d, dd in (mat.get("domains") or {}).items() if d != dom
                     for rid in (dd.get("ratings") or {})}
        mine = (({r["id"] for r in groups.get(dom, [])} | {r.get("req") for r in data.get("ratings") or []})
                - elsewhere)
        seen, rated = set(), {}
        for n, row in enumerate(data.get("ratings") or [], 1):
            rid = row.get("req")
            where = f"ratings {n} ({rid})"
            if rid not in reqs:
                problems.append(f"{where}: unknown requirement")
                continue
            if rid in elsewhere:
                problems.append(f"{where}: already rated in another domain "
                                f"({next(d for d, dd in mat['domains'].items() if rid in (dd.get('ratings') or {}))})")
            if rid in seen:
                problems.append(f"{where}: rated twice")
            seen.add(rid)
            if row.get("level") not in lv:
                problems.append(f"{where}: level {row.get('level')!r} is not one of {', '.join(lv)}")
                continue
            level = lv[row["level"]]
            if level.get("gap") and not (row.get("what_fails") or "").strip():
                problems.append(f"{where}: {row['level']} counts as a gap, so say in `what_fails` "
                                "what we can't meet — Stage 4 needs it for the mitigation")
            mod = (row.get("module") or "").strip()
            if mod and mod not in P.catalogue(packs):
                problems.append(f"{where}: module {mod!r} isn't in the pack catalogue")
            ev = []
            for m, e in enumerate(row.get("evidence") or [], 1):
                if e.get("kind") not in kinds:
                    problems.append(f"{where} evidence {m}: kind must be one of {', '.join(kinds)}")
                    continue
                cite = (e.get("cite") or "").strip()
                if not cite:
                    problems.append(f"{where} evidence {m}: give `cite` — what shows it")
                    continue
                # exists vs verified: citing something that isn't there is an error; citing a catalogue
                # entry the pack hasn't sourced is allowed, and prints as unverified — the gate is where
                # that gets confronted, not the save.
                exists, ok, why = evidence.verify(deal, cite, blocks)
                if not exists:
                    problems.append(f"{where} evidence {m}: {cite} — {why}")
                ev.append({"kind": e["kind"], "cite": cite, "exists": exists, "verified": ok})
            if level.get("counts_as") not in ("none",) and not ev and row["level"] != "unassessed":
                problems.append(f"{where}: {row['level']} with no evidence: either cite something or rate it "
                                "unassessed (a rating with no evidence prints as unverified)")
            rated[rid] = {"level": row["level"], "module": mod or None, "evidence": ev,
                          "what_fails": (row.get("what_fails") or "").strip(), "note": (row.get("note") or "").strip(),
                          "suggested": D.module_for(reqs[rid], packs)}
        missing = sorted(mine - set(rated))
        if missing and not data.get("partial"):
            problems.append(f"{len(missing)} requirement(s) in {dom} not rated: {', '.join(missing[:12])}"
                            + (" …" if len(missing) > 12 else "") + " (or set `partial: true` to save a draft)")
        if problems:
            return None, problems
        cur = mat["domains"].setdefault(dom, {})
        cur.update({"ratings": {**rated}, "done": not missing,
                    "unknowns": data.get("unknowns") or [], "confirms": data.get("confirms") or [],
                    "saved": f"{dt.date.today():%Y-%m-%d}", "partial": bool(missing)})
        mat["version"] += 1
        files.write(_matrix_path(deal), mat)
        _register(deal, f"stage3:{dom}", data)
        return dom, []

    # scope overview
    doms = data.get("domains") or {}
    if not doms:
        problems.append("write the scope overview: `domains` (or rate a domain with `ratings`)")
    declared = P.domains(packs)
    for k, v in doms.items():
        if k not in declared:
            problems.append(f"domains.{k}: not declared by any product pack")
        if not (v or {}).get("note"):
            problems.append(f"domains.{k}: say what the buyer wants there")
    for n, o in enumerate(data.get("out_of_scope") or [], 1):
        ids = o.get("sources") or []
        if not ids:
            problems.append(f"out_of_scope {n}: cite what excludes it")
        bad = [i for i in ids if i not in blocks and i not in reqs]
        if bad:
            problems.append(f"out_of_scope {n}: unknown source {', '.join(bad)}")
    if problems:
        return None, problems
    mat["scope"] = {"domains": doms, "out_of_scope": data.get("out_of_scope") or [],
                    "statistics": data.get("statistics") or {}, "saved": f"{dt.date.today():%Y-%m-%d}"}
    mat["version"] += 1
    files.write(_matrix_path(deal), mat)
    _register(deal, "stage3:scope", data)
    return "scope", []


def _register(deal, tag, data):
    registers.replace_stage(deal, tag,
                            [{"kind": "U", "text": u["text"], "source": u.get("sources")}
                             for u in data.get("unknowns") or []]
                            + [{"kind": "C", "text": c.get("text") or c.get("question"), "role": c.get("role"),
                                "question": c.get("question")} for c in data.get("confirms") or []])


# ---------------------------------------------------------------- the numbers
def matrix(deal, config):
    packs, _ = P.load(deal, config)
    lv = levels(config)
    mat = load(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    rows, counts, gaps, unverified = [], {k: 0 for k in lv}, [], []
    for dom, d in mat["domains"].items():
        for rid, r in (d.get("ratings") or {}).items():
            if rid not in reqs:
                continue
            level = lv.get(r["level"]) or {}
            verified = any(e.get("verified") for e in r.get("evidence") or [])
            counts[r["level"]] = counts.get(r["level"], 0) + 1
            if level.get("counts_as") not in ("none",) and not verified:
                unverified.append(rid)
            row = {"req": rid, "domain": dom, "level": r["level"], "level_label": level.get("label", r["level"]),
                   "counts_as": level.get("counts_as"), "gap": bool(level.get("gap")),
                   "module": r.get("module"), "evidence": r.get("evidence") or [],
                   "verified": verified, "what_fails": r.get("what_fails", ""), "note": r.get("note", ""),
                   "text": reqs[rid]["text"], "obligation": reqs[rid]["obligation"],
                   "type": reqs[rid]["type"], "blocks": reqs[rid]["blocks"]}
            if row["gap"]:
                gaps.append((rid, row))          # the row, not the raw rating: callers read level_label etc.
            rows.append(row)
    covered = sum(1 for x in rows if x["counts_as"] == "covered")
    total_domains = len(grouped(deal, config))
    done_domains = sum(1 for d in mat["domains"].values() if d.get("done"))
    return {"rows": rows, "counts": counts, "gaps": gaps, "unverified": unverified,
            "requirements": len(reqs), "rated": len(rows), "covered": covered,
            "complete": len(rows) == len(reqs), "domains_done": done_domains, "domains_total": total_domains,
            "scope": mat.get("scope"), "version": mat.get("version", 0),
            "mandatory_gaps": [rid for rid, r in gaps if reqs[rid]["obligation"] in ("mandatory", "disqualifier")]}


# ---------------------------------------------------------------- render
def render(deal, config):
    pack_list, pack_problems = P.load(deal, config)
    if pack_problems:
        return None, pack_problems
    m = matrix(deal, config)
    if not m["complete"]:
        return None, [f"the matrix isn't complete: {m['rated']} of {m['requirements']} requirements rated "
                      f"({m['domains_done']}/{m['domains_total']} domains done)"]
    blocks = load_blocks(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    lv = levels(config)
    doms = P.domains(pack_list)
    bid = deal.bid()
    regs = {i["id"]: i for i in registers.items(deal)}
    st = state.load(deal)
    version = st["stages"].get("stage3", {}).get("version", 0) + 1
    c = lambda ids: "; ".join(R.cite(blocks[i]) for i in ids or [] if i in blocks) or "—"

    L = ["# Stage 3 — Scope & requirements", "",
         f"{bid.get('customer')} · {bid.get('rfp')} · version {version} · {dt.date.today():%d %b %Y}", "",
         f"> {m['rated']} of {m['requirements']} requirements rated · {m['covered']} covered "
         f"({m['covered'] / max(m['rated'], 1):.0%}) · {len(m['gaps'])} gaps "
         f"({len(m['mandatory_gaps'])} mandatory or disqualifying) · {len(m['unverified'])} unverified", ""]

    sc = m["scope"] or {}
    L += ["## 3.1 Scope", ""]
    if sc.get("domains"):
        L += ["| Domain | What the buyer wants | Requirements | Covered |", "|---|---|---|---|"]
        for key, note in sc["domains"].items():
            rows = [x for x in m["rows"] if x["domain"] == key]
            L.append(f"| {doms.get(key, {}).get('label', key)} | {(note or {}).get('note', '')} | {len(rows)} | "
                     f"{sum(1 for x in rows if x['counts_as'] == 'covered')} |")
        L += [""]
    if sc.get("out_of_scope"):
        L += ["**Out of scope:**"] + [f"- {o['text']} ({c(o.get('sources'))})" for o in sc["out_of_scope"]] + [""]

    L += ["## 3.2 Compliance matrix", ""]
    for key in {x["domain"] for x in m["rows"]}:
        rows = [x for x in m["rows"] if x["domain"] == key]
        L += [f"### {doms.get(key, {}).get('label', key)} ({len(rows)})", "",
              "| REQ | Requirement | Level | Module | Evidence | Note |", "|---|---|---|---|---|---|"]
        for x in sorted(rows, key=lambda r: (0 if r["gap"] else 1, r["req"])):
            flag = {"disqualifier": "**[DISQUALIFIER]** ", "mandatory": "**[MANDATORY]** "}.get(x["obligation"], "")
            level = x["level_label"] + (" **→ gap**" if x["gap"] else "")
            if x["counts_as"] not in ("none",) and not x["verified"]:
                level += " *(unverified)*"
            evd = "; ".join(f"{e['kind']}: {e['cite']}" + ("" if e.get("verified") else " (UNVERIFIED)")
                            for e in x["evidence"]) or "—"
            note = x["what_fails"] or x["note"] or ""
            L.append(f"| {x['req']} | {flag}{x['text'][:150]}<br>*(⁠{c(reqs[x['req']]['blocks'])}⁠)* | {level} | "
                     f"{x['module'] or '—'} | {evd} | {note} |")
        L += [""]

    nfr_types = set((config["compliance"] or {}).get("nfr_types") or [])
    nfrs = [x for x in m["rows"] if x["type"] in nfr_types]
    if nfrs:
        L += ["## 3.3 Non-functional requirements", "",
              "| REQ | NFR | Type | Level | Evidence |", "|---|---|---|---|---|"]
        L += [f"| {x['req']} | {x['text'][:140]} | {x['type']} | {x['level_label']}"
              + ("" if x["verified"] else " *(unverified)*") + " | "
              + ("; ".join(e["cite"] for e in x["evidence"]) or "—") + " |" for x in nfrs]
        L += [""]

    L += ["## 3.4 Fit at a glance", "", "| Level | Count | Share |", "|---|---|---|"]
    for k, v in lv.items():
        n = m["counts"].get(k, 0)
        if n:
            L.append(f"| {v.get('label', k)} | {n} | {n / max(m['rated'], 1):.0%} |")
    if m["gaps"]:
        L += ["", f"**Gaps to mitigate in Stage 4 ({len(m['gaps'])}):**"]
        L += [f"- {rid} ({x['level_label']}): {x['what_fails'] or x['note']}" for rid, x in m["gaps"][:40]]
        if len(m["gaps"]) > 40:
            L.append(f"- … and {len(m['gaps']) - 40} more")
    if m["unverified"]:
        L += ["", f"**Unverified ratings ({len(m['unverified'])}):** {', '.join(m['unverified'][:30])}"
              + (" …" if len(m["unverified"]) > 30 else ""),
              "", "These carry a level but nothing that shows it. They are the first thing a red team "
              "will pull apart, and the first place to spend evidence time."]

    L += ["", "---", "", "**Gate checklist**",
          f"- [ ] {config['stages']['stage3'].get('gate_check', '')}",
          "- [ ] Every requirement rated; no requirement dropped or merged",
          "- [ ] Every gap has `what_fails` and goes to Stage 4",
          "- [ ] Unverified ratings either sourced or accepted as open items", "",
          "**Open Unknown / Confirm items from this stage**"]
    mine = [i for i in regs.values() if str(i.get("stage", "")).startswith("stage3") and i.get("status") == "open"]
    L += [f"- {i['id']}: {i['text']}" + (f" — ask {i['role']}: {i['question']}" if i.get("role") else "")
          for i in mine] or ["- none"]
    L += ["", "**Recommended next step:** pass the Stage 3 gate, then Stage 4 (solution & licensing)."]
    return m, ["\n".join(L) + "\n"]


def save_render(deal, config):
    """Write stages/stage-3.md once the matrix is complete (keeps the previous version)."""
    m, out = render(deal, config)
    if out and not m:
        return None, out
    st = state.load(deal)
    prev = st["stages"].get("stage3", {})
    version = prev.get("version", 0) + 1
    path = deal.path / "stages" / "stage-3.md"
    if path.exists():
        path.rename(deal.path / "stages" / f"stage-3.v{version - 1}.md")
    path.write_text(out[0], encoding="utf-8")
    # a re-render keeps a gate that was already passed: the ratings didn't change, only the document did
    st["stages"]["stage3"] = {"done": True, "gate_passed": bool(prev.get("gate_passed")), "version": version,
                              "saved": f"{dt.date.today():%Y-%m-%d}",
                              **({"gate_note": prev["gate_note"], "gate_date": prev["gate_date"]}
                                 if prev.get("gate_passed") else {}),
                              "gaps": len(m["gaps"]), "unverified": len(m["unverified"])}
    state.save(deal, st)
    return path, []
