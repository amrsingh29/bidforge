"""Stage 2 — Qualification (bid / no-bid).

    brief(deal, config) -> text      Stage 1 summary, capture inputs (and which are missing), evaluation text,
                                     every pass/fail requirement, the scorecard, the JSON to write
    score(data, config) -> dict      weighted total, knockouts, and the recommendation the numbers give
    save(deal, data, config) -> (path of stage-2.md, problems)

The model writes the judgement (context, each pass/fail item's can-we-meet-it, a 1–5 score per criterion
with its reasons); the code checks the sources, makes sure every pass/fail item is assessed, works out
the weighted score and the recommendation, and refuses a decision that contradicts them without an
override reason. A criterion that can't be scored yet (score null) leaves the decision Pending.
"""
import datetime as dt, re

from core.intake.run import load_blocks
from core.stages.stage1 import LABELS
from core.store import capture, files, registers, state
from core.store import requirements as R

EVALUATION = re.compile(r"evaluat|weightage|weighting|\bscor(?:e|es|ing)\b|criteri|passing mark|shortlist|lowest (?:price|bid)|"
                        r"best value|two.envelope|technical (?:and|&) commercial|demonstration|proof of concept|\bPOC\b", re.I)


def criteria(config):
    sc = (config.get("qualification") or {}).get("scorecard") or {}
    return {k: v for k, v in sc.items() if isinstance(v, dict) and v.get("enabled", True)}


def passfail(deal):
    """Requirements whose failure excludes the bid: every disqualifier."""
    return [r for r in R.load(deal)["items"] if r["obligation"] == "disqualifier"]


# ---------------------------------------------------------------- brief for the model
def brief(deal, config):
    q = config["qualification"]
    blocks = load_blocks(deal)
    s1 = files.read(deal.path / "data" / "stage1.json", {})
    cap = capture.load(deal)
    L = ["# Stage 2 brief", ""]
    sm = s1.get("summary") or {}
    if sm:
        L += ["## From Stage 1",
              f"- Customer: {sm.get('customer', {}).get('text', '')}",
              f"- What they want: {sm.get('outcomes', {}).get('text', '')}",
              f"- Why now: {sm.get('why_now', {}).get('text', '')}",
              f"- Scope: {sm.get('scope', {}).get('text', '')}",
              f"- Initial fit: {sm.get('fit')}", ""]
    L += ["## Capture inputs (from the user; the pack can't tell us these)"]
    for k, question in q["capture"].items():
        L.append(f"- {k}: " + (f"{cap[k]['value']}  (from {cap[k]['by']}, {cap[k]['date']})" if k in cap
                               else f"MISSING — ask: {question}"))
    miss = capture.missing(deal, config)
    if miss:
        L += ["", f"**Ask the user for the {len(miss)} missing input(s) before scoring** "
                  "(`bid capture KEY=\"answer\"`). Criteria that depend on a missing input get score null."]
    L += ["", "## Blocks about evaluation, scoring and award"]
    L += [f"{b['id']} {R.cite(b)}: {b['text'][:300]}" for b in blocks.values()
          if b["kind"] != "heading" and EVALUATION.search(b["text"])][:80] or ["(none found: say the method is not stated)"]
    pf = passfail(deal)
    L += ["", f"## Pass/fail requirements — assess every one ({len(pf)})"]
    L += [f"{r['id']} [{r['type']}] {r['text'][:220]}  ({R.cite(blocks[r['blocks'][0]])})" for r in pf]
    L += ["", "## Scorecard (1 = poor … 5 = strong; null if it can't be scored yet)"]
    L += [f"- {k}: {v['label']} — weight {v['weight']} — {v.get('ask', '')}" for k, v in criteria(config).items()]
    th = q["thresholds"]
    L += [f"Bid at ≥ {th['bid']}/100; Bid with conditions at ≥ {th['conditions']}; else No-bid. "
          f"Any pass/fail item marked {' / '.join(q['knockout_on'])} means No-bid unless you give an override reason.",
          "", "## Write this JSON (sources: block IDs, REQ IDs, or capture:KEY)", "```json",
          _json(TEMPLATE(config)), "```"]
    return "\n".join(L)


def _json(x):
    import json
    return json.dumps(x, indent=1, ensure_ascii=False)


def TEMPLATE(config):
    item = {"text": "", "label": "Stated|Inferred|Unknown", "sources": ["B-…", "REQ-…", "capture:KEY"]}
    return {
        "context": {"current_state": item, "pains": [item], "success_criteria": [item], "stakeholders": [item],
                    "signals": [{"text": "wired-RFP sign, competitor wording, odd specifics, unrealistic timeline", "label": "Inferred", "sources": []}]},
        "evaluation": {"method": item, "weights": [{"criterion": "", "weight": "", "sources": []}],
                       "concentration": item, "competitors": [{"name": "", "positioning": "", "label": "Inferred", "sources": []}]},
        "mandatory": [{"req": "REQ-…", "can_meet": "|".join(config["qualification"]["can_meet"]),
                       "evidence": "what shows we can (empty = unverified)", "note": "", "owner": "role key"}],
        "scorecard": [{"criterion": k, "score": "1-5 or null", "rationale": "", "label": "Stated|Inferred|Unknown",
                       "sources": []} for k in criteria(config)],
        "decision": {"recommendation": "|".join(config["qualification"]["decisions"]),
                     "conditions": ["what must be true to bid"], "override_reason": ""},
        "unknowns": [{"text": "", "sources": []}],
        "confirms": [{"text": "", "role": "", "question": ""}],
    }


# ---------------------------------------------------------------- the numbers
def score(data, config):
    q = config["qualification"]
    crit = criteria(config)
    rows = {s.get("criterion"): s for s in data.get("scorecard") or []}
    pending = [k for k in crit if rows.get(k, {}).get("score") is None]
    total = sum((rows[k]["score"] - 1) / 4 * v["weight"] for k, v in crit.items() if k not in pending)
    max_known = sum(v["weight"] for k, v in crit.items() if k not in pending)
    knock = [m["req"] for m in data.get("mandatory") or [] if m.get("can_meet") in q["knockout_on"]]
    at_risk = [m["req"] for m in data.get("mandatory") or [] if m.get("can_meet") in ("At risk", "Unknown")]
    th = q["thresholds"]
    if pending:
        rec = "Pending"
    elif knock:
        rec = "No-bid"
    elif total >= th["bid"]:
        rec = "Bid"
    elif total >= th["conditions"]:
        rec = "Bid with conditions"
    else:
        rec = "No-bid"
    return {"total": round(total, 1), "scored_weight": max_known, "pending": pending, "knockouts": knock,
            "at_risk": at_risk, "recommendation": rec}


# ---------------------------------------------------------------- save and render
def save(deal, data, config):
    q = config["qualification"]
    blocks = load_blocks(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    cap = capture.load(deal)
    roles = config.get("roles") or {}
    problems = []
    st = state.load(deal)
    if not st["stages"].get("stage1", {}).get("gate_passed"):
        problems.append("the Stage 1 gate hasn't been passed (bid gate pass stage1)")

    def src(item, where, required=True):
        ids = item.get("sources") or []
        if required and not ids and item.get("label") != "Unknown":
            problems.append(f"{where}: no sources (or label it Unknown)")
        for i in ids:
            if i.startswith("capture:"):
                if i[8:] not in cap:
                    problems.append(f"{where}: {i} isn't recorded (bid capture {i[8:]}=\"…\")")
            elif i not in blocks and i not in reqs:
                problems.append(f"{where}: unknown source {i}")

    def labelled(item, where):
        if item.get("label") not in LABELS:
            problems.append(f"{where}: label must be Stated, Inferred or Unknown")
        src(item, where)

    ctx = data.get("context") or {}
    for k in ("current_state", "pains", "success_criteria", "stakeholders", "signals"):
        v = ctx.get(k)
        if v is None:
            problems.append(f"context.{k}: missing (use an item labelled Unknown if the pack doesn't say)")
            continue
        for n, it in enumerate(v if isinstance(v, list) else [v], 1):
            labelled(it, f"context.{k} {n}")
    ev = data.get("evaluation") or {}
    for k in ("method", "concentration"):
        if k not in ev:
            problems.append(f"evaluation.{k}: missing")
        else:
            labelled(ev[k], f"evaluation.{k}")
    for n, c in enumerate(ev.get("competitors") or [], 1):
        labelled(c, f"evaluation.competitors {n}")
    for n, w in enumerate(ev.get("weights") or [], 1):
        src(w, f"evaluation.weights {n}")

    want = {r["id"] for r in passfail(deal)}
    seen = {}
    for n, m in enumerate(data.get("mandatory") or [], 1):
        rid = m.get("req")
        if rid not in reqs:
            problems.append(f"mandatory {n}: unknown requirement {rid}")
            continue
        if rid not in want:
            problems.append(f"mandatory {n}: {rid} is not a pass/fail requirement (typo?)")
        seen[rid] = seen.get(rid, 0) + 1
        if m.get("can_meet") not in q["can_meet"]:
            problems.append(f"mandatory {rid}: can_meet must be one of {', '.join(q['can_meet'])}")
        if m.get("owner") and m["owner"] not in roles:
            problems.append(f"mandatory {rid}: owner {m['owner']!r} is not a role (bid config show roles)")
    missing = sorted(want - set(seen))
    if missing:
        problems.append(f"{len(missing)} pass/fail requirement(s) not assessed: {', '.join(missing[:15])}"
                        + (" …" if len(missing) > 15 else ""))
    dup = [k for k, v in seen.items() if v > 1]
    if dup:
        problems.append(f"assessed more than once: {', '.join(dup)}")

    crit = criteria(config)
    rows = {}
    for n, s in enumerate(data.get("scorecard") or [], 1):
        k = s.get("criterion")
        if k not in crit:
            problems.append(f"scorecard {n}: unknown criterion {k!r} (criteria: {', '.join(crit)})")
            continue
        rows[k] = s
        sc = s.get("score")
        if sc is not None and (not isinstance(sc, int) or not 1 <= sc <= 5):
            problems.append(f"scorecard {k}: score must be 1–5, or null if it can't be scored yet")
        if not (s.get("rationale") or "").strip():
            problems.append(f"scorecard {k}: give the rationale")
        if sc is not None and s.get("label") == "Unknown":
            problems.append(f"scorecard {k}: a score labelled Unknown is a guess: use null, or say what it rests on")
        labelled(s, f"scorecard {k}")
    for k in crit:
        if k not in rows:
            problems.append(f"scorecard: {k} not scored (use null if it can't be yet)")

    numbers = score(data, config)
    dec = data.get("decision") or {}
    rec = dec.get("recommendation")
    if rec not in q["decisions"] + ["Pending"]:
        problems.append(f"decision.recommendation: one of {', '.join(q['decisions'])}, or Pending")
    elif numbers["recommendation"] == "Pending" and rec != "Pending":
        problems.append(f"decision: criteria not scored yet ({', '.join(numbers['pending'])}), so the decision is Pending")
    elif rec != numbers["recommendation"] and not (dec.get("override_reason") or "").strip():
        problems.append(f"decision: the numbers give {numbers['recommendation']} ({numbers['total']}/100"
                        + (f", knockouts {', '.join(numbers['knockouts'])}" if numbers["knockouts"] else "")
                        + f"), not {rec}: change it or give an override_reason")
    if rec == "Bid with conditions" and not dec.get("conditions"):
        problems.append("decision: Bid with conditions needs the conditions")
    for n, u in enumerate(data.get("unknowns") or [], 1):
        src(u, f"unknowns {n}")
    for n, c in enumerate(data.get("confirms") or [], 1):
        if not c.get("role") or not c.get("question"):
            problems.append(f"confirms {n}: give the role and the exact question")
    if problems:
        return None, problems

    reg = registers.replace_stage(deal, "stage2",
                                  [{"kind": "U", "text": u["text"], "source": u.get("sources")} for u in data.get("unknowns") or []]
                                  + [{"kind": "C", "text": c["text"] or c["question"], "role": c["role"], "question": c["question"]}
                                     for c in data.get("confirms") or []])
    files.write(deal.path / "data" / "stage2.json", data)
    prev = st["stages"].get("stage2", {})
    version = prev.get("version", 0) + 1
    out = deal.path / "stages" / "stage-2.md"
    if out.exists():
        out.rename(deal.path / "stages" / f"stage-2.v{version - 1}.md")
    out.write_text(render(deal, data, numbers, reg, config, version), encoding="utf-8")
    st["stages"]["stage2"] = {"done": True, "gate_passed": False, "version": version, "saved": f"{dt.date.today():%Y-%m-%d}",
                              "recommendation": rec, "score": numbers["total"]}
    state.save(deal, st)
    return out, []


def render(deal, data, numbers, reg_ids, config, version):
    blocks = load_blocks(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    cap = capture.load(deal)
    q = config["qualification"]

    def c(ids):
        out = []
        for i in ids or []:
            if i.startswith("capture:"):
                out.append(f"capture: {i[8:]} ({cap.get(i[8:], {}).get('by', '?')})")
            elif i in reqs:
                out.append(i)
            elif i in blocks:
                out.append(R.cite(blocks[i]))
        return "; ".join(out) or "—"

    def line(it):
        return f"{it['text']} — *{it['label']}* ({c(it.get('sources'))})"

    bid = deal.bid()
    dec = data["decision"]
    L = ["# Stage 2 — Qualification (bid / no-bid)", "",
         f"{bid.get('customer')} · {bid.get('rfp')} · version {version} · {dt.date.today():%d %b %Y}", "",
         f"> **Recommendation: {dec['recommendation']}** — weighted score {numbers['total']}/100"
         + (f" so far, out of the {numbers['scored_weight']} points scored (still to score: {', '.join(numbers['pending'])})" if numbers["pending"] else "")
         + (f" · knockouts: {', '.join(numbers['knockouts'])}" if numbers["knockouts"] else "")
         + (f" · override: {dec['override_reason']}" if dec.get("override_reason") else ""), ""]
    if dec.get("conditions"):
        L += ["**Conditions:**"] + [f"- {x}" for x in dec["conditions"]] + [""]

    ctx = data["context"]
    L += ["## 2.1 Customer context & drivers", ""]
    for k, title in (("current_state", "Current state"), ("pains", "Pain points"), ("success_criteria", "Success criteria / KPIs"),
                     ("stakeholders", "Stakeholders and decision makers"), ("signals", "Hidden signals")):
        v = ctx[k] if isinstance(ctx[k], list) else [ctx[k]]
        L += [f"**{title}**"] + [f"- {line(it)}" for it in v] + [""]

    ev = data["evaluation"]
    L += ["## 2.2 Evaluation criteria (first view)", "", f"**Method.** {line(ev['method'])}", ""]
    if ev.get("weights"):
        L += ["| Criterion | Weight | Source |", "|---|---|---|"] + [
            f"| {w['criterion']} | {w['weight']} | {c(w.get('sources'))} |" for w in ev["weights"]] + [""]
    L += [f"**Where the points are.** {line(ev['concentration'])}", ""]
    if ev.get("competitors"):
        L += ["**Likely competitors**"] + [f"- {x['name']}: {x['positioning']} — *{x['label']}* ({c(x.get('sources'))})"
                                           for x in ev["competitors"]] + [""]

    L += ["## 2.3 Mandatory & disqualifying requirements", "",
          "| Requirement | Can we meet it? | Evidence | Owner | Note |", "|---|---|---|---|---|"]
    order = {"No": 0, "At risk": 1, "Unknown": 2, "Yes": 3}
    for m in sorted(data["mandatory"], key=lambda m: (order.get(m["can_meet"], 9), m["req"])):
        r = reqs[m["req"]]
        verdict = m["can_meet"] + ("" if m["can_meet"] != "Yes" or (m.get("evidence") or "").strip() else " *(unverified)*")
        L.append(f"| **[DISQUALIFIER]** {m['req']}: {r['text'][:160]} ({R.cite(blocks[r['blocks'][0]])}) | {verdict} | "
                 f"{m.get('evidence') or '—'} | {m.get('owner') or '—'} | {m.get('note') or ''} |")
    counts = {k: sum(1 for m in data["mandatory"] if m["can_meet"] == k) for k in q["can_meet"]}
    L += ["", "Totals: " + " · ".join(f"{k} {v}" for k, v in counts.items()), ""]

    L += ["## 2.4 Bid / no-bid scorecard", "", "| Criterion | Weight | Score | Rationale | Label | Source |", "|---|---|---|---|---|---|"]
    rows = {s["criterion"]: s for s in data["scorecard"]}
    for k, v in criteria(config).items():
        s = rows[k]
        L.append(f"| {v['label']} | {v['weight']} | {s['score'] if s['score'] is not None else '—'} | {s['rationale']} | "
                 f"{s['label']} | {c(s.get('sources'))} |")
    th = q["thresholds"]
    L += ["", f"Weighted total **{numbers['total']}/100** (Bid ≥ {th['bid']}, Bid with conditions ≥ {th['conditions']}). "
          + (f"Not decidable until scored: {', '.join(numbers['pending'])}." if numbers["pending"] else "")]

    regs = {i["id"]: i for i in registers.items(deal)}
    L += ["", "---", "", "**Gate checklist**",
          f"- [ ] {config['stages']['stage2'].get('gate_check', '')}",
          "- [ ] Every pass/fail item marked No or At risk has an owner and a plan",
          "- [ ] Capture inputs confirmed by the account team", "",
          "**New Unknown / Confirm items**"]
    L += [f"- {i}: {regs[i]['text']}" + (f" — ask {regs[i]['role']}: {regs[i]['question']}" if regs[i].get("role") else "")
          for i in reg_ids] or ["- none"]
    nxt = {"Bid": "pass the Stage 2 gate with the AE, then Stage 3 (scope & requirements).",
           "Bid with conditions": "agree the conditions with the AE, pass the Stage 2 gate, then Stage 3.",
           "No-bid": "agree the no-bid with the AE and share the rationale above; the analysis stops here.",
           "Pending": "get the missing inputs, re-run Stage 2, then decide."}[dec["recommendation"]]
    L += ["", f"**Recommended next step:** {nxt}"]
    return "\n".join(L) + "\n"
