"""Stage 4 — Solution & licensing: what we propose, how each gap closes, and what to ask before pricing.

    brief(deal, config) -> text                gaps from the matrix, modules in scope, the inputs Deal Desk
                                               has to answer, and the JSON to write
    save(deal, data, config) -> (path, problems)
    inputs(deal, config) -> dict               what's still missing before this stage is done

The stage is where invention is most tempting, so the checks are tight:
  - every gap Stage 3 found has a mitigation, and a roadmap mitigation is never "closes it"
  - a module named in the solution must exist in a product pack, and it must be a module Stage 3 rated
    a requirement against (or the code says so)
  - every licensing, sizing and services input is either recorded with who gave it, or raised as a
    Confirm item for the role that can answer
  - no number is accepted: licence counts, prices and days are the deal team's, recorded verbatim
  - a scope rule that names `forbid` words refuses a claim at save rather than in review

The forbidden vocabulary belongs to the pack, not to this module: the engine has no idea which words are
sales-poison for a given product, so a rule carries them (`scope_rules: - forbid: [...]`) and a pack with
no such rule simply has nothing to block. Hardcoding one vendor's exclusions here would have made the
engine quietly product-specific.
"""
import datetime as dt

from core import packs as P
from core.intake.run import load_blocks
from core.stages import stage3
from core.store import files, registers, state
from core.store import requirements as R


def mitigations(config):
    return {k: v for k, v in ((config.get("solution") or {}).get("mitigations") or {}).items()
            if isinstance(v, dict) and v.get("enabled", True)}


def _path(deal):
    return deal.path / "data" / "stage4.json"


def load(deal):
    return files.read(_path(deal), {})


def gaps(deal, config):
    """Every gap Stage 3 found, with the row it came from."""
    m = stage3.matrix(deal, config)
    rows = {r["req"]: r for r in m["rows"]}
    return [rows[rid] for rid, _ in m["gaps"] if rid in rows]


# ---------------------------------------------------------------- what the model reads
def brief(deal, config):
    pack_list, pack_problems = P.load(deal, config)
    if pack_problems:
        return "# Stage 4 brief\n\n" + "\n".join(f"✗ {p}" for p in pack_problems)
    m = stage3.matrix(deal, config)
    if not m["complete"]:
        return (f"# Stage 4\n\nThe Stage 3 matrix isn't complete ({m['rated']} of {m['requirements']} rated). "
                "Finish Stage 3 first.")
    blocks = load_blocks(deal)
    gs = gaps(deal, config)
    L = ["# Stage 4 brief — solution & licensing", ""]
    L += ["## Proposed scope (from the Stage 3 matrix)", ""]
    mods = {}
    for x in m["rows"]:
        if x["counts_as"] in ("covered", "partial") and x["module"]:
            mods.setdefault(x["module"], []).append(x["req"])
    if mods:
        L += ["| Module | Requirements it covers |", "|---|---|"]
        L += [f"| {k} | {len(v)} ({', '.join(v[:8])}{' …' if len(v) > 8 else ''}) |" for k, v in mods.items()]
    else:
        L += ["No module was named in the matrix: say which modules the solution proposes."]
    L += ["", "## Gaps to mitigate — every one needs a mitigation", ""]
    L += [f"{x['req']} [{x['level_label']}] {x['text'][:150]}\n    what fails: {x['what_fails'] or x['note'] or '—'}"
          for x in gs] or ["- none"]
    L += ["", "## Mitigations", ""]
    L += [f"- `{k}` — {v.get('label')}" + ("" if v.get("closes_it") else " (**does not close the gap**)")
          + (f": {v.get('note')}" if v.get("note") else "") for k, v in mitigations(config).items()]
    rules = P.scope_rules(pack_list)
    if rules:
        L += ["", "## Scope rules (a claim that breaks one is refused at save)"]
        L += [f"- **{r['id']}**: {' '.join(str(r['text']).split())}" for r in rules]
    L += ["", "## Meetings to ask the buyer", ""] + [f"- {q}" for q in (config["solution"].get("solution_questions") or [])]
    L += ["", "## Licensing inputs — ask Deal Desk; never estimate", ""]
    have = load(deal).get("licensing") or {}
    L += [f"- {i['key']}" + (f": **{have[i['key']]['value']}** (from {have[i['key']]['by']})" if i["key"] in have else f": {i['ask']}")
          for i in _pack_inputs(pack_list, "licensing_inputs")]
    L += ["", "## Sizing inputs", ""]
    L += [f"- {i['key']}" + (f": **{have[i['key']]['value']}**" if i["key"] in have else f": {i['ask']}")
          for i in _pack_inputs(pack_list, "sizing_inputs")]
    L += ["", "## Services inputs", ""]
    L += [f"- {i['key']}" + (f": **{have[i['key']]['value']}**" if i["key"] in have else f": {i['ask']}")
          for i in _pack_inputs(pack_list, "services_inputs")]
    L += ["", "## Architecture sections to write", ""] + [f"- {s}" for s in (config["solution"].get("architecture_sections") or [])]
    L += ["", "## Write this JSON", "```json", _json(TEMPLATE(config, pack_list, gs, mods)), "```"]
    return "\n".join(L)


def _pack_inputs(pack_list, key):
    out = []
    for p in pack_list:
        for i in ((p["meta"].get(key)) or []):
            out.append(dict(i, pack=p["id"]))
    return out


def _json(x):
    import json
    return json.dumps(x, indent=1, ensure_ascii=False)


def TEMPLATE(config, pack_list, gs, mods):
    return {
        "modules": [{"module": k, "why": "what it does for this buyer", "reqs": ["REQ-…"]}
                    for k in (list(mods)[:2] or ["module key from the pack catalogue"])],
        "mitigations": [{"req": x["req"], "how": "|".join(mitigations(config)), "detail": "",
                         "owner": "role key"} for x in gs[:2]] or [{"req": "REQ-…", "how": "…", "detail": "", "owner": ""}],
        "architecture": {s: {"text": "", "sources": ["REQ-…", "B-…"]}
                         for s in (config["solution"].get("architecture_sections") or [])},
        "integrations": [{"system": "", "direction": "inbound|outbound|both", "how": "",
                          "sources": ["REQ-…"]}],
        "licensing": [{"key": "key from the licensing inputs", "value": "as given, with the model and metric",
                       "by": "who gave it", "role": "deal_desk"}],
        "sizing": [{"key": "", "value": "", "by": "", "role": "presales"}],
        "services": [{"key": "", "value": "effort band", "by": "", "role": "professional_services"}],
        "unknowns": [{"text": "", "sources": ["REQ-…"]}],
        "confirms": [{"text": "", "role": "deal_desk", "question": "the exact question to ask"}],
    }


# ---------------------------------------------------------------- save
def save(deal, data, config):
    pack_list, pack_problems = P.load(deal, config)
    problems = list(pack_problems)
    st = state.load(deal)
    if not st["stages"].get("stage2", {}).get("gate_passed"):
        problems.append("the Stage 2 gate hasn't been passed")
    m = stage3.matrix(deal, config)
    if not m["complete"]:
        problems.append(f"the Stage 3 matrix isn't complete ({m['rated']} of {m['requirements']} rated)")
    blocks = load_blocks(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    roles = config.get("roles") or {}
    cat = P.catalogue(pack_list)
    mit = mitigations(config)
    rules = P.scope_rules(pack_list)

    def src(item, where, required=True):
        ids = item.get("sources") or []
        if required and not ids:
            problems.append(f"{where}: no sources")
        bad = [i for i in ids if i not in blocks and i not in reqs]
        if bad:
            problems.append(f"{where}: unknown source {', '.join(bad)}")

    # modules must exist, and must be ones Stage 3 actually rated something against
    used = {x["module"] for x in m["rows"] if x["module"]}
    rows_by_req = {x["req"]: x for x in m["rows"]}
    mods = {}
    for n, mod in enumerate(data.get("modules") or [], 1):
        key = mod.get("module")
        if key not in cat:
            problems.append(f"modules {n}: {key!r} isn't in the pack catalogue")
            continue
        if key in mods:
            problems.append(f"modules {n}: {key} listed twice")
        mods[key] = mod
        if not (mod.get("why") or "").strip():
            problems.append(f"modules {key}: say what it does for this buyer")
        if key not in used:
            problems.append(f"modules {key}: no Stage 3 requirement is rated against it "
                            "(rate the requirements first, or leave the module out)")
        # a module names the requirements it answers; it doesn't need block sources of its own
        listed = mod.get("reqs") or []
        if not listed:
            problems.append(f"modules {key}: name the requirements it answers in `reqs`")
        bad = [x for x in listed if x not in reqs]
        if bad:
            problems.append(f"modules {key}: unknown requirement(s) {', '.join(bad)}")
        wrongly = [x for x in listed if x in reqs and (rows_by_req.get(x) or {}).get("module") not in (None, key)]
        if wrongly:
            problems.append(f"modules {key}: {', '.join(wrongly)} is rated against a different module in the matrix")
    unproposed = used - set(mods)
    if unproposed:
        problems.append(f"modules: {', '.join(sorted(unproposed))} carry ratings in the matrix but aren't "
                        "in the proposed solution (add them, or re-rate those requirements)")

    # every gap mitigated, and a roadmap never closes one
    want = {x["req"] for x in gaps(deal, config)}
    seen = {}
    for n, mt in enumerate(data.get("mitigations") or [], 1):
        rid = mt.get("req")
        where = f"mitigations {n} ({rid})"
        if rid not in reqs:
            problems.append(f"{where}: unknown requirement")
            continue
        if rid not in want:
            problems.append(f"{where}: {rid} isn't a Stage 3 gap (nothing to mitigate)")
        seen[rid] = mt
        if mt.get("how") not in mit:
            problems.append(f"{where}: how must be one of {', '.join(mit)}")
            continue
        if not (mt.get("detail") or "").strip():
            problems.append(f"{where}: give the detail — what exactly closes it, or why it stays open")
        if not mt.get("owner"):
            problems.append(f"{where}: give an owner role")
        elif mt["owner"] not in roles:
            problems.append(f"{where}: {mt['owner']!r} is not a role")
        if mt["how"] == "roadmap":
            # roadmap is never a closure; make sure the record says so rather than relying on prose
            mt["closes_it"] = False
        else:
            mt["closes_it"] = bool(mit[mt["how"]].get("closes_it"))
    missing = sorted(want - set(seen))
    if missing:
        problems.append(f"{len(missing)} gap(s) with no mitigation: {', '.join(missing[:12])}"
                        + (" …" if len(missing) > 12 else ""))

    # A scope rule may name words the solution must not claim. The rule carries the vocabulary, so a
    # pack with no such rule blocks nothing, and a private pack can forbid whatever it needs to.
    text_all = " ".join(str(v) for v in [*(data.get("modules") or []), *(data.get("architecture") or {}).values()]).lower()
    for rule in rules:
        forbid = [w for w in (rule.get("forbid") or []) if w]
        if not forbid:
            continue
        hits = [w for w in forbid if w.lower() in text_all]
        if hits and not (rule.get("allow_with") and any(
                mt.get("how") in rule["allow_with"] for mt in data.get("mitigations") or [])):
            problems.append(f"scope rule {rule['id']}: the solution claims {', '.join(hits)}. "
                            + " ".join(str(rule.get("text") or "").split())[:200]
                            + (f" Allowed only with: {', '.join(rule['allow_with'])}." if rule.get("allow_with") else ""))

    arch = data.get("architecture") or {}
    for s in (config["solution"].get("architecture_sections") or []):
        if not (arch.get(s) or {}).get("text"):
            problems.append(f"architecture.{s}: missing")
        else:
            src(arch[s], f"architecture.{s}")

    for n, integ in enumerate(data.get("integrations") or [], 1):
        if not integ.get("system") or not integ.get("how"):
            problems.append(f"integrations {n}: give the system and how it connects")
        src(integ, f"integrations {n}")

    # inputs: recorded with who gave them, or a confirm item. No numbers invented.
    given = {}
    for field, key in (("licensing", "licensing_inputs"), ("sizing", "sizing_inputs"), ("services", "services_inputs")):
        allowed = {i["key"] for i in _pack_inputs(pack_list, key)}
        for n, it in enumerate(data.get(field) or [], 1):
            where = f"{field} {n} ({it.get('key')})"
            if it.get("key") not in allowed:
                problems.append(f"{where}: not one of the {field} inputs")
                continue
            if not (it.get("value") or "").strip():
                problems.append(f"{where}: empty value (leave the item out if it isn't known yet)")
            if not (it.get("by") or "").strip():
                problems.append(f"{where}: say who gave it (`by`)")
            if it.get("role") and it["role"] not in roles:
                problems.append(f"{where}: role {it['role']!r} doesn't exist")
            given.setdefault(field, {})[it["key"]] = it["value"]
    confirms = {}
    for n, c in enumerate(data.get("confirms") or [], 1):
        if not c.get("role") or not c.get("question"):
            problems.append(f"confirms {n}: give the role and the exact question")
            continue
        if c["role"] not in roles:
            problems.append(f"confirms {n}: role {c['role']!r} doesn't exist")
        confirms[c.get("text") or c["question"]] = c
    for field, key in (("licensing", "licensing_inputs"), ("sizing", "sizing_inputs"), ("services", "services_inputs")):
        for i in _pack_inputs(pack_list, key):
            if i["key"] in (given.get(field) or {}):
                continue
            if not any(i["key"] in (c.get("text") or "") + (c.get("question") or "") for c in confirms.values()):
                problems.append(f"{field}.{i['key']}: neither recorded nor raised as a Confirm item "
                                f"— ask it, or record the answer with who gave it ({i['ask'][:80]}…)")
    for n, u in enumerate(data.get("unknowns") or [], 1):
        src(u, f"unknowns {n}")

    if problems:
        return None, problems

    data["_gaps"] = {rid: {"closes_it": mt.get("closes_it"), "how": mt.get("how")} for rid, mt in seen.items()}
    files.write(_path(deal), data)
    registers.replace_stage(deal, "stage4",
                            [{"kind": "U", "text": u["text"], "source": u.get("sources")} for u in data.get("unknowns") or []]
                            + [{"kind": "C", "text": c.get("text") or c.get("question"), "role": c["role"],
                                "question": c["question"]} for c in data.get("confirms") or []])
    prev = st["stages"].get("stage4", {})
    version = prev.get("version", 0) + 1
    out = deal.path / "stages" / "stage-4.md"
    if out.exists():
        out.rename(deal.path / "stages" / f"stage-4.v{version - 1}.md")
    out.write_text(render(deal, data, config, pack_list, m, seen, version), encoding="utf-8")
    st["stages"]["stage4"] = {"done": True, "gate_passed": False, "version": version,
                              "saved": f"{dt.date.today():%Y-%m-%d}",
                              "open_gaps": sum(1 for x in seen.values() if not x.get("closes_it"))}
    state.save(deal, st)
    return out, []


def inputs(deal, config):
    """What's recorded, and what's still only a question."""
    pack_list, _ = P.load(deal, config)
    data = load(deal)
    out = {}
    for field, key in (("licensing", "licensing_inputs"), ("sizing", "sizing_inputs"), ("services", "services_inputs")):
        have = {i.get("key"): i for i in data.get(field) or []}
        want = [i["key"] for i in _pack_inputs(pack_list, key)]
        out[field] = {"have": [k for k in want if k in have], "missing": [k for k in want if k not in have]}
    return out


# ---------------------------------------------------------------- render
def render(deal, data, config, pack_list, m, seen, version):
    blocks = load_blocks(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    bid = deal.bid()
    mit = mitigations(config)
    cat = P.catalogue(pack_list)
    c = lambda ids: "; ".join(R.cite(blocks[i]) for i in ids or [] if i in blocks) or "—"
    L = ["# Stage 4 — Solution & licensing", "",
         f"{bid.get('customer')} · {bid.get('rfp')} · version {version} · {dt.date.today():%d %b %Y}", ""]

    L += ["## 4.1 Proposed solution", "", "| Module | What it does here | Requirements | Pack |", "|---|---|---|---|"]
    for mod in data["modules"]:
        e = cat.get(mod["module"]) or {}
        L.append(f"| {e.get('covers', mod['module']).split(',')[0]} (`{mod['module']}`) | {mod['why']} | "
                 f"{', '.join(mod.get('reqs') or []) or '—'} | {e.get('pack', '—')} |")

    L += ["", "## 4.2 Architecture outline", ""]
    for s, v in (data.get("architecture") or {}).items():
        L += [f"**{s.replace('_', ' ').capitalize()}.** {v['text']} ({c(v.get('sources'))})", ""]

    if data.get("integrations"):
        L += ["## 4.3 Integrations", "", "| System | Direction | How | Source |", "|---|---|---|---|"]
        L += [f"| {i['system']} | {i.get('direction', '—')} | {i['how']} | {c(i.get('sources'))} |"
              for i in data["integrations"]] + [""]

    L += ["## 4.4 Gaps and mitigations", "", "| REQ | Level | What fails | How | Detail | Closes it? | Owner |",
          "|---|---|---|---|---|---|---|"]
    rows = {r["req"]: r for r in m["rows"]}
    for rid, mt in seen.items():
        x = rows.get(rid, {})
        closes = "✅ yes" if mt.get("closes_it") else "❌ **no — open**"
        how = (mit.get(mt["how"]) or {}).get("label", mt["how"])
        if mt["how"] == "roadmap":
            how = "**[ROADMAP RISK]** " + how
        L.append(f"| {rid} | {x.get('level_label', '')} | {x.get('what_fails') or '—'} | {how} | {mt.get('detail', '')} "
                 f"| {closes} | {mt.get('owner') or '—'} |")
    open_gaps = [rid for rid, mt in seen.items() if not mt.get("closes_it")]
    L += ["", f"**{len(seen)} gaps mitigated; {len(open_gaps)} remain open**"
          + (f": {', '.join(open_gaps)}" if open_gaps else "") + ".", ""]

    L += ["## 4.5 Licensing, sizing and services inputs", "",
          "Recorded answers only. BidForge does not estimate licence metrics, quantities or prices.", ""]
    for title, field in (("Licensing", "licensing"), ("Sizing", "sizing"), ("Services", "services")):
        items = data.get(field) or []
        L += [f"**{title}**", ""]
        L += [f"- {i['key']}: {i['value']}" + (f" — from {i['by']}" if i.get("by") else "") for i in items] or ["- none recorded"]
        L += [""]
    if data.get("confirms"):
        L += ["**Questions raised (not yet answered):**"] + [f"- ask {c0['role']}: {c0['question']}"
                                                            for c0 in data["confirms"]] + [""]

    L += ["---", "", "**Gate checklist**",
          f"- [ ] {config['stages']['stage4'].get('gate_check', '')}",
          "- [ ] Every gap has a mitigation; open ones are visible", "",
          "**Recommended next step:** send the Deal Desk and Product Management questions, then Stage 5 "
          "(security, compliance & legal)."]
    return "\n".join(L) + "\n"
