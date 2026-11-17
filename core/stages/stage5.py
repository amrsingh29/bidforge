"""Stage 5 — Security, compliance & legal: route the slow items early, with an owner and a date.

    brief(deal, config) -> text                security and legal requirements, the region packs' regulations,
                                               the standing items nobody escapes, AI checks when they apply,
                                               the clause watch list, and the JSON to write
    save(deal, data, config) -> (path, problems)

This stage exists because Security and Legal are the two queues that sink bids near the deadline. So the
checks are about handover, not prose:
  - every security and legal requirement found in the pack is answered or explicitly deferred with a reason
  - every item that goes to Security or Legal has an owner role and a due date inside the bid calendar
  - a certification is only claimed with the certificate cited (fixed rule 3)
  - regulations from the region and industry packs are checked against the RFP: applied, or not mentioned
  - AI checks appear when the RFP or the solution involves AI, and each one gets an answer or a question
"""
import datetime as dt, re

from core import packs as P
from core.intake.run import load_blocks
from core.stages import stage3
from core.store import capture, files, registers, state
from core.store import requirements as R

AI = re.compile(r"\bAI\b|\bA\.I\.|artificial intelligence|machine learning|\bML\b|virtual agent|"
                r"chatbot|large language|LLM|generative|predictive|algorithm|automation that decides|"
                r"auto-?classif|natural language|\bNLU\b|\bNLP\b", re.I)
CERT = re.compile(r"ISO\s?\d{4,5}|SOC\s?2|MTCS|IRAP|FedRAMP|PCI[\s-]?DSS|Cyber Essentials|"
                  r"ISO/IEC\s?\d+|CSA STAR|\bTISAX\b|\bHIPAA\b", re.I)


def clause_risks(config):
    return {k: v for k, v in ((config.get("security") or {}).get("clause_risks") or {}).items()
            if isinstance(v, dict) and v.get("enabled", True)}


def _path(deal):
    return deal.path / "data" / "stage5.json"


def load(deal):
    return files.read(_path(deal), {})


def relevant(deal, config):
    """(security requirements, legal requirements, clause-bearing blocks) from the extraction."""
    reqs = R.load(deal)["items"]
    sec = [r for r in reqs if r["type"] == "security"]
    legal = [r for r in reqs if r["type"] == "legal"]
    blocks = load_blocks(deal)
    clause = [b for b in blocks.values() if re.search(r"liabilit|indemnif|termination|indemnity|"
                                                      r"service credits|liquidated damages|governing law|"
                                                      r"warranty|insur|audit right|confidential", b["text"], re.I)]
    return sec, legal, clause


def ai_in_scope(deal, config):
    """AI checks apply when the RFP or the proposed solution mentions it. Returns the hits, or []."""
    blocks = load_blocks(deal)
    hits = [b for b in blocks.values() if AI.search(b["text"])]
    sol = load(deal)
    sol_text = " ".join(str(v) for v in [*(sol.get("modules") or []), *(sol.get("architecture") or {}).values()])
    if AI.search(sol_text):
        hits.append({"id": "stage4", "text": "the proposed solution involves AI or automation"})
    return hits


# ---------------------------------------------------------------- what the model reads
def brief(deal, config):
    pack_list, pack_problems = P.load(deal, config)
    if pack_problems:
        return "# Stage 5 brief\n\n" + "\n".join(f"✗ {p}" for p in pack_problems)
    blocks = load_blocks(deal)
    sec, legal, clause = relevant(deal, config)
    s = config["security"]
    dates = state.deadlines(deal)
    L = ["# Stage 5 brief — security, compliance & legal", ""]
    if dates:
        L += ["## The clock", ""] + [f"- {d['name']}: {d['date']}" for d in dates] + [""]

    L += [f"## Security requirements from the pack ({len(sec)}) — answer each or defer with a reason", ""]
    L += [f"{r['id']} {r['text'][:200]}  ({R.cite(blocks[r['blocks'][0]]) if r['blocks'] else '—'})" for r in sec] or ["- none found"]

    L += ["", f"## Legal requirements from the pack ({len(legal)})", ""]
    L += [f"{r['id']} {r['text'][:200]}  ({R.cite(blocks[r['blocks'][0]]) if r['blocks'] else '—'})" for r in legal] or ["- none found"]

    certs = sorted({m.group(0) for b in blocks.values() for m in CERT.finditer(b["text"])})
    if certs:
        L += ["", f"## Certifications mentioned in the pack: {', '.join(certs)}",
              "Claim only what you can cite (fixed rule 3). A claim with no certificate is Unknown with a Confirm item."]

    L += ["", "## Standing items nobody escapes", ""]
    L += [f"- `{i['key']}` — {i['label']}" for i in (s.get("standing_items") or [])]

    regs = P.regulations(pack_list)
    if regs:
        L += ["", "## Regulations from the region and industry packs", "",
              "For each: is it raised by the RFP? If yes, cite the clause and say what is required. "
              "If the RFP doesn't mention it, say so — that is a finding, not a silence.", "",
              "| Regulation | Pack | Owner | Raised by |", "|---|---|---|---|"]
        L += [f"| {r['name']} | {r['pack']} | {r.get('owner', '—')} | {r.get('raises', '')} |" for r in regs]

    ai = ai_in_scope(deal, config)
    if ai:
        L += ["", f"## AI checks apply ({len(ai)} mention(s) in the pack or the solution)", ""]
        L += [f"- {c0}" for c0 in P.ai_checks(pack_list, config)]
    else:
        L += ["", "## AI checks", "Not triggered: neither the pack nor the proposed solution mentions AI. "
              "If you believe they apply anyway, say so in `ai_trigger`."]

    L += ["", "## Clauses to rate", ""]
    L += [f"- `{i['key']}` — {i['label']}" for i in (s.get("clause_watch") or [])]
    L += ["", "Levels: " + ", ".join(f"`{k}` ({v.get('label')})" for k, v in clause_risks(config).items())]
    if clause:
        L += ["", f"## Blocks that look like contract language ({len(clause)}) — cite these when rating a clause", ""]
        L += [f"{b['id']} {R.cite(b)}: {b['text'][:220]}" for b in clause[:60]]

    L += ["", "## Write this JSON", "```json", _json(TEMPLATE(config, pack_list, sec, legal, regs, ai, certs)), "```"]
    return "\n".join(L)


def _json(x):
    import json
    return json.dumps(x, indent=1, ensure_ascii=False)


def TEMPLATE(config, pack_list, sec, legal, regs, ai, certs):
    s = config["security"]
    return {
        "security": [{"req": "REQ-…", "answer": "Yes|No|Partial|Deferred", "evidence": "cite: library id, confirm:KEY, pack:module",
                      "note": "", "owner": "security", "due": "YYYY-MM-DD"} for _ in sec[:2]],
        "standing": [{"key": i["key"], "answer": "", "evidence": "", "owner": "security", "due": "YYYY-MM-DD"}
                     for i in (s.get("standing_items") or [])[:2]],
        "certifications": [{"name": certs[0] if certs else "", "claimed": "Yes|No|Unknown",
                            "evidence": "the certificate or report, cited", "note": ""}],
        "regulations": [{"name": r["name"], "pack": r["pack"], "applies": "Yes|No|Not mentioned",
                         "sources": ["B-…"], "requirement": "", "owner": "security", "due": "YYYY-MM-DD"} for r in regs[:2]],
        "ai_trigger": "",
        "ai": [{"check": c0, "answer": "", "sources": ["B-…"], "owner": "security", "due": "YYYY-MM-DD"} for c0 in (P.ai_checks(pack_list, config) if ai else [])[:2]],
        "legal": [{"req": "REQ-…", "answer": "", "owner": "legal", "due": "YYYY-MM-DD"} for _ in legal[:1]],
        "clauses": [{"key": i["key"], "found": "the clause as written, or 'not in the pack'", "risk": "|".join(clause_risks(config)),
                     "sources": ["B-…"], "position": "what we can accept, and what we must change", "owner": "legal",
                     "due": "YYYY-MM-DD"} for i in (s.get("clause_watch") or [])[:2]],
        "handovers": [{"to": "security|legal", "item": "", "owner": "role key", "due": "YYYY-MM-DD"}],
        "unknowns": [{"text": "", "sources": ["B-…", "REQ-…"]}],
        "confirms": [{"text": "", "role": "security", "question": ""}],
    }


# ---------------------------------------------------------------- save
def save(deal, data, config):
    pack_list, pack_problems = P.load(deal, config)
    problems = list(pack_problems)
    st = state.load(deal)
    if not st["stages"].get("stage2", {}).get("gate_passed"):
        problems.append("the Stage 2 gate hasn't been passed")
    blocks = load_blocks(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    roles = config.get("roles") or {}
    s = config["security"]
    risks = clause_risks(config)
    sec, legal, _ = relevant(deal, config)
    regs = P.regulations(pack_list)
    ai = ai_in_scope(deal, config)
    dates = {d["date"] for d in state.deadlines(deal) if d.get("date")}
    deadline = max(dates) if dates else None
    today = f"{dt.date.today():%Y-%m-%d}"

    def owner_due(item, where):
        o = item.get("owner")
        if s.get("handover", {}).get("require_owner", True):
            if not o:
                problems.append(f"{where}: no owner (Security and Legal items are handed over, not noted)")
            elif o not in roles:
                problems.append(f"{where}: {o!r} is not a role")
        if s.get("handover", {}).get("require_due_date", True):
            due = item.get("due")
            if not due:
                problems.append(f"{where}: no due date")
            else:
                try:
                    dt.date.fromisoformat(due)
                except ValueError:
                    problems.append(f"{where}: due must be YYYY-MM-DD")
                else:
                    if due < today:
                        problems.append(f"{where}: due {due} is in the past")
                    if deadline and due > deadline:
                        problems.append(f"{where}: due {due} is after the response deadline {deadline}")

    def ev(item, where, required=True):
        cite = (item.get("evidence") or "").strip()
        if not cite:
            if required:
                problems.append(f"{where}: no evidence — cite a library id, confirm:KEY, pack:module or the certificate")
            return
        from core import evidence
        # Stage 5 is a handover, not a rating: an unsourced catalogue entry doesn't show anything Security
        # can sign, so here it is refused rather than printed as unverified.
        exists, ok, why = evidence.verify(deal, cite, blocks)
        if not exists:
            problems.append(f"{where}: {cite} — {why}")
        elif not ok:
            problems.append(f"{where}: {cite} is a catalogue entry with no source and nothing confirmed — "
                            "cite the certificate, the document or a confirmation")
        item["_verified"] = ok

    # security requirements
    want_sec = {r["id"] for r in sec}
    seen_sec = {}
    for n, it in enumerate(data.get("security") or [], 1):
        rid = it.get("req")
        where = f"security {n} ({rid})"
        if rid not in reqs:
            problems.append(f"{where}: unknown requirement")
            continue
        if rid not in want_sec:
            problems.append(f"{where}: not a security requirement")
        seen_sec[rid] = it
        if it.get("answer") not in ("Yes", "No", "Partial", "Deferred"):
            problems.append(f"{where}: answer must be Yes, No, Partial or Deferred")
        if it.get("answer") in ("Yes", "Partial"):
            ev(it, where)
        elif it.get("answer") == "Deferred" and not (it.get("note") or "").strip():
            problems.append(f"{where}: Deferred needs a reason in `note`")
        owner_due(it, where)
    missing = sorted(want_sec - set(seen_sec))
    if missing:
        problems.append(f"{len(missing)} security requirement(s) not answered: {', '.join(missing[:12])}"
                        + (" …" if len(missing) > 12 else ""))

    # standing items: all of them, or it isn't a security review
    seen_stand = {}
    for n, it in enumerate(data.get("standing") or [], 1):
        key = it.get("key")
        where = f"standing {n} ({key})"
        if key not in {i["key"] for i in (s.get("standing_items") or [])}:
            problems.append(f"{where}: not one of the standing items")
            continue
        seen_stand[key] = it
        if not (it.get("answer") or "").strip():
            problems.append(f"{where}: give the answer")
        else:
            ev(it, where)
        owner_due(it, where)
    miss_stand = {i["key"] for i in (s.get("standing_items") or [])} - set(seen_stand)
    if miss_stand:
        problems.append(f"standing items not covered: {', '.join(sorted(miss_stand))}")

    # certifications: never claimed without the document
    for n, cert in enumerate(data.get("certifications") or [], 1):
        name = cert.get("name") or f"certifications {n}"
        if cert.get("claimed") not in ("Yes", "No", "Unknown"):
            problems.append(f"certifications {n}: claimed must be Yes, No or Unknown")
        if cert.get("claimed") == "Yes":
            ev(cert, f"certifications ({name})")
        elif cert.get("claimed") == "Unknown" and not (cert.get("note") or "").strip():
            problems.append(f"certifications ({name}): Unknown needs the reason and the Confirm item")

    # regulations: applied, not mentioned, or not applicable — all three are answers
    seen_reg = {}
    for n, it in enumerate(data.get("regulations") or [], 1):
        name = it.get("name")
        where = f"regulations {n} ({name})"
        if name not in {r["name"] for r in regs}:
            problems.append(f"{where}: not a regulation any pack lists")
            continue
        seen_reg[name] = it
        if it.get("applies") not in ("Yes", "No", "Not mentioned"):
            problems.append(f"{where}: applies must be Yes, No or Not mentioned")
        if not (it.get("sources") or []):
            problems.append(f"{where}: cite what raised it (or the clause that is silent about it)")
        bad = [x for x in it.get("sources") or [] if x not in blocks and x not in reqs]
        if bad:
            problems.append(f"{where}: unknown source {', '.join(bad)}")
        if it.get("applies") == "Yes":
            if not (it.get("requirement") or "").strip():
                problems.append(f"{where}: say what the RFP actually requires")
            owner_due(it, where)
    miss_reg = {r["name"] for r in regs} - set(seen_reg)
    if miss_reg:
        problems.append(f"regulations not assessed: {', '.join(sorted(miss_reg))}")

    # AI: checked when triggered, and an explicit 'not triggered' reason when it isn't
    if ai:
        got = {a.get("check") for a in data.get("ai") or []}
        want_ai = set(P.ai_checks(pack_list, config))
        if not data.get("ai"):
            problems.append("AI is mentioned in the pack or the solution, so the AI checks apply: answer them")
        for n, a in enumerate(data.get("ai") or [], 1):
            where = f"ai {n}"
            if a.get("check") not in want_ai:
                problems.append(f"{where}: not one of the AI checks")
            if not (a.get("answer") or "").strip():
                problems.append(f"{where}: give the answer")
            if not (a.get("sources") or []):
                problems.append(f"{where}: cite where it comes up")
            owner_due(a, where)
        miss = want_ai - got
        if miss:
            problems.append(f"AI checks unanswered: {len(miss)} of {len(want_ai)}")
    elif not (data.get("ai_trigger") or "").strip():
        problems.append("AI checks weren't triggered by the pack: say why in `ai_trigger` "
                        "(or state the trigger if you think they apply)")

    # legal requirements
    want_legal = {r["id"] for r in legal}
    seen_legal = {}
    for n, it in enumerate(data.get("legal") or [], 1):
        rid = it.get("req")
        where = f"legal {n} ({rid})"
        if rid not in reqs:
            problems.append(f"{where}: unknown requirement")
            continue
        if rid not in want_legal:
            problems.append(f"{where}: not a legal requirement")
        seen_legal[rid] = it
        if not (it.get("answer") or "").strip():
            problems.append(f"{where}: give the position")
        owner_due(it, where)
    miss_legal = sorted(want_legal - set(seen_legal))
    if miss_legal:
        problems.append(f"{len(miss_legal)} legal requirement(s) not answered: {', '.join(miss_legal[:12])}"
                        + (" …" if len(miss_legal) > 12 else ""))

    # clauses: every watched clause has a position
    seen_cl = {}
    for n, cl in enumerate(data.get("clauses") or [], 1):
        key = cl.get("key")
        where = f"clauses {n} ({key})"
        if key not in {i["key"] for i in (s.get("clause_watch") or [])}:
            problems.append(f"{where}: not a watched clause")
            continue
        seen_cl[key] = cl
        if cl.get("risk") not in risks:
            problems.append(f"{where}: risk must be one of {', '.join(risks)}")
        if not (cl.get("found") or "").strip():
            problems.append(f"{where}: say what the clause says, or that it isn't in the pack")
        elif not (cl.get("position") or "").strip():
            problems.append(f"{where}: give our position — what we accept, what we must change")
        if not (cl.get("sources") or []):
            problems.append(f"{where}: cite the clause (or the block where it should be)")
        bad = [x for x in cl.get("sources") or [] if x not in blocks and x not in reqs]
        if bad:
            problems.append(f"{where}: unknown source {', '.join(bad)}")
        if cl.get("risk") in ("high", "unknown"):
            owner_due(cl, where)
    miss_cl = {i["key"] for i in (s.get("clause_watch") or [])} - set(seen_cl)
    if miss_cl:
        problems.append(f"clauses not assessed: {', '.join(sorted(miss_cl))}")

    for n, h in enumerate(data.get("handovers") or [], 1):
        if h.get("to") not in ("security", "legal"):
            problems.append(f"handovers {n}: to must be security or legal")
        if not (h.get("item") or "").strip():
            problems.append(f"handovers {n}: what is being handed over")
        owner_due(h, f"handovers {n}")

    for n, u in enumerate(data.get("unknowns") or [], 1):
        ids = u.get("sources") or []
        if not ids:
            problems.append(f"unknowns {n}: no sources")
        bad = [x for x in ids if x not in blocks and x not in reqs]
        if bad:
            problems.append(f"unknowns {n}: unknown source {', '.join(bad)}")
    for n, c0 in enumerate(data.get("confirms") or [], 1):
        if not c0.get("role") or not c0.get("question"):
            problems.append(f"confirms {n}: give the role and the exact question")

    if problems:
        return None, problems

    files.write(_path(deal), data)
    registers.replace_stage(deal, "stage5",
                            [{"kind": "U", "text": u["text"], "source": u.get("sources")} for u in data.get("unknowns") or []]
                            + [{"kind": "C", "text": c0.get("text") or c0.get("question"), "role": c0["role"],
                                "question": c0["question"]} for c0 in data.get("confirms") or []])
    prev = st["stages"].get("stage5", {})
    version = prev.get("version", 0) + 1
    out = deal.path / "stages" / "stage-5.md"
    if out.exists():
        out.rename(deal.path / "stages" / f"stage-5.v{version - 1}.md")
    out.write_text(render(deal, data, config, version), encoding="utf-8")
    high = sum(1 for c0 in data.get("clauses") or [] if c0.get("risk") in ("high", "unknown"))
    st["stages"]["stage5"] = {"done": True, "gate_passed": False, "version": version,
                              "saved": f"{dt.date.today():%Y-%m-%d}", "high_risk_clauses": high}
    state.save(deal, st)
    return out, []


# ---------------------------------------------------------------- render
def render(deal, data, config, version):
    blocks = load_blocks(deal)
    reqs = {r["id"]: r for r in R.load(deal)["items"]}
    bid = deal.bid()
    s = config["security"]
    risks = clause_risks(config)
    c = lambda ids: "; ".join(R.cite(blocks[i]) if i in blocks else i for i in ids or []) or "—"
    L = ["# Stage 5 — Security, compliance & legal", "",
         f"{bid.get('customer')} · {bid.get('rfp')} · version {version} · {dt.date.today():%d %b %Y}", ""]

    L += ["## 5.1 Security requirements", "", "| REQ | Requirement | Answer | Evidence | Owner | Due |",
          "|---|---|---|---|---|---|"]
    for it in data.get("security") or []:
        r = reqs.get(it["req"], {})
        L.append(f"| {it['req']} | {r.get('text', '')[:140]} | {it['answer']} | {it.get('evidence') or '—'} | "
                 f"{it.get('owner', '—')} | {it.get('due', '—')} |")
    L += ["", f"**Standing items**", "", "| Item | Answer | Evidence | Owner | Due |", "|---|---|---|---|---|"]
    labels = {i["key"]: i["label"] for i in (s.get("standing_items") or [])}
    for it in data.get("standing") or []:
        L.append(f"| {labels.get(it['key'], it['key'])} | {it['answer']} | {it.get('evidence') or '—'} | "
                 f"{it.get('owner', '—')} | {it.get('due', '—')} |")

    if data.get("certifications"):
        L += ["", "## 5.2 Certifications", "", "| Certification | Claimed | Evidence | Note |", "|---|---|---|---|"]
        L += [f"| {x['name']} | {x['claimed']}" + ("" if x.get("evidence") else " *(unverified)*")
              + f" | {x.get('evidence') or '—'} | {x.get('note') or ''} |" for x in data["certifications"]]

    if data.get("regulations"):
        L += ["", "## 5.3 Regulatory & data residency", "",
              "| Regulation | Applies | What it requires | Source | Owner | Due |", "|---|---|---|---|---|---|"]
        L += [f"| {x['name']} ({x.get('pack', '')}) | {x['applies']} | {x.get('requirement') or '—'} | "
              f"{c(x.get('sources'))} | {x.get('owner', '—')} | {x.get('due', '—')} |" for x in data["regulations"]]

    if data.get("ai") or data.get("ai_trigger"):
        L += ["", "## 5.4 AI-specific checks", ""]
        if data.get("ai"):
            L += ["| Check | Answer | Source | Owner | Due |", "|---|---|---|---|---|"]
            L += [f"| {x['check']} | {x['answer']} | {c(x.get('sources'))} | {x.get('owner', '—')} | {x.get('due', '—')} |"
                  for x in data["ai"]]
        else:
            L += [data["ai_trigger"]]

    if data.get("legal"):
        L += ["", "## 5.5 Legal requirements", "", "| REQ | Requirement | Position | Owner | Due |",
              "|---|---|---|---|---|"]
        L += [f"| {x['req']} | {reqs.get(x['req'], {}).get('text', '')[:140]} | {x['answer']} | "
              f"{x.get('owner', '—')} | {x.get('due', '—')} |" for x in data["legal"]]

    L += ["", "## 5.6 Clause risk table", "", "| Clause | Found | Risk | Our position | Source | Owner | Due |",
          "|---|---|---|---|---|---|---|"]
    for x in data.get("clauses") or []:
        label = {i["key"]: i["label"] for i in (s.get("clause_watch") or [])}.get(x["key"], x["key"])
        rk = (risks.get(x["risk"]) or {}).get("label", x["risk"])
        mark = "🔴 " if x["risk"] == "high" else ("🟠 " if x["risk"] == "medium" else "")
        L.append(f"| {label} | {x['found'][:120]} | {mark}{rk} | {x.get('position') or '—'} | "
                 f"{c(x.get('sources'))} | {x.get('owner', '—')} | {x.get('due', '—')} |")
    high = [x for x in data.get("clauses") or [] if x["risk"] in ("high", "unknown")]
    if high:
        L += ["", f"**{len(high)} clause(s) need Legal before we submit:** "
                  + ", ".join({i['key']: i['label'] for i in (s.get('clause_watch') or [])}.get(x["key"], x["key"]) for x in high)]

    if data.get("handovers"):
        L += ["", "## 5.7 Handovers", "", "| To | Item | Owner | Due |", "|---|---|---|---|"]
        L += [f"| {x['to'].capitalize()} | {x['item']} | {x.get('owner', '—')} | {x.get('due', '—')} |"
              for x in data["handovers"]]

    regs = {i["id"]: i for i in registers.items(deal)}
    L += ["", "---", "", "**Gate checklist**",
          f"- [ ] {config['stages']['stage5'].get('gate_check', '')}",
          "- [ ] Every Security and Legal item has an owner and a date", "",
          "**Open Unknown / Confirm items from this stage**"]
    mine = [i for i in regs.values() if i.get("stage") == "stage5" and i.get("status") == "open"]
    L += [f"- {i['id']}: {i['text']}" + (f" — ask {i['role']}: {i['question']}" if i.get("role") else "") for i in mine] or ["- none"]
    L += ["", "**Recommended next step:** hand the items over, then Stage 6 (roles, risks & clarifications)."]
    return "\n".join(L) + "\n"
