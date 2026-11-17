"""Stage 1 — Inventory & understanding.

    brief(deal) -> text      what the model needs: the mechanical inventory, blocks holding dates and
                             submission rules, documents referenced but not in the pack, the JSON to write
    save(deal, data, config) -> (path of stage-1.md, problems)    nothing is written if there are problems

The model writes the judgement (what each document contains, the dates, the rules, the summary);
the code checks every item cites real blocks, that Stated dates are really in the source, and renders
stages/stage-1.md with the coverage report. Earlier versions are kept as stage-1.vN.md.
"""
import datetime as dt, json, re

from core.intake import coverage
from core.intake.run import docs, load_blocks
from core.store import files, registers, state
from core.store import requirements as R

DOC_TYPES = ["main RFP", "annex", "form", "questionnaire", "compliance matrix", "pricing schedule", "Q&A",
             "SOW", "T&Cs", "NDA", "other"]
LABELS = {"Stated", "Inferred", "Unknown"}
FLAGS = {"", "MANDATORY", "DISQUALIFIER"}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DATE_TEXT = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(\d{4})"
                       r"|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"
                       r"|\b(\d{4})-(\d{2})-(\d{2})\b|\b(\d{1,2})/(\d{1,2})/(\d{4})\b", re.I)
REFERENCE = re.compile(r"\b(?:Annex|Appendix|Schedule|Attachment|Exhibit|Form|Template)\s+[A-Z0-9][\w.-]*"
                       r"|\b[A-Z]{2,}(?:-[A-Z0-9]{2,}){2,}\b|\b[\w-]+\.(?:xlsx|docx|pdf|xls|doc)\b")
SUBMISSION = re.compile(r"submi|proposal (?:structure|format|response)|response requirement|page limit|portal|envelope|"
                        r"bid bond|deadline", re.I)


def dates_in(text):
    """ISO dates written in a text (day-month-year, month-day-year, ISO, d/m/y)."""
    out = set()
    for m in DATE_TEXT.finditer(text):
        g = m.groups()
        try:
            if g[0]:
                out.add(dt.date(int(g[2]), MONTHS[g[1][:3].lower()], int(g[0])))
            elif g[3]:
                out.add(dt.date(int(g[5]), MONTHS[g[3][:3].lower()], int(g[4])))
            elif g[6]:
                out.add(dt.date(int(g[6]), int(g[7]), int(g[8])))
            else:
                out.add(dt.date(int(g[11]), int(g[10]), int(g[9])))
        except ValueError:
            pass
    return {d.isoformat() for d in out}


# ---------------------------------------------------------------- brief for the model
def brief(deal):
    blocks = load_blocks(deal).values()
    ds = docs(deal)
    names = {d["name"].lower() for d in ds} | {d["name"].rsplit(".", 1)[0].lower() for d in ds}
    headings = " ".join(b["text"].lower() for b in blocks if b["kind"] == "heading")
    lines = ["# Stage 1 brief", "", "## Pack (from the code pass)"]
    for d in ds:
        extra = ", ".join(f"{k} {v}" for k, v in d["stats"].items() if v)
        lines.append(f"- {d['name']} [{d['kind']}] {d['blocks']} blocks, {d['candidates']} candidates"
                     + (f", {extra}" if extra else "") + ("; BUYER COMPLIANCE MATRIX" if d["matrix"] else "")
                     + "".join(f"; NOT READ: {u['what']} ({u['why']})" for u in d["unread"]))
    refs = {}
    for b in blocks:
        for m in REFERENCE.findall(b["text"]):
            ref = m.strip(".")
            low = ref.lower()
            if low in headings or any(low in n or n.startswith(low) for n in names):
                continue
            refs.setdefault(ref, b["id"])
    lines += ["", "## Referenced in the text but not matched to a pack file or heading (decide which are really missing)"]
    lines += [f"- {r} (first in {bid})" for r, bid in list(refs.items())[:60]] or ["- none"]
    lines += ["", "## Blocks with dates or deadlines"]
    for b in blocks:
        if dates_in(b["text"]) or re.search(r"business days|deadline|TBC|closing date|due", b["text"], re.I):
            lines.append(f"{b['id']} {b['doc']} {b['loc']}: {b['text'][:300]}")
    lines += ["", "## Blocks about submission (format, structure, limits, portal, signatures)"]
    for b in blocks:
        if b["kind"] != "heading" and (SUBMISSION.search(b.get("heading") or "") or SUBMISSION.search(b["text"])):
            lines.append(f"{b['id']} {b['doc']} {b['loc']}: {b['text'][:300]}")
    lines += ["", "## Write this JSON (every `sources` lists block IDs; labels: Stated | Inferred | Unknown)", "```json",
              json.dumps(TEMPLATE, indent=1, ensure_ascii=False), "```"]
    return "\n".join(lines)


TEMPLATE = {
    "documents": [{"file": "exact file name", "type": "|".join(DOC_TYPES), "contains": "one line",
                   "readable": "Y|N|Partial"}],
    "missing": [{"reference": "what the text refers to", "sources": ["B-…"], "note": ""}],
    "forms": [{"name": "form or template to fill", "file": "file, or empty if it isn't in the pack", "sources": ["B-…"]}],
    "dates": [{"milestone": "", "as_written": "exactly as the source says (e.g. +14 Business Days, TBC)",
               "date": "YYYY-MM-DD or null", "time": "", "timezone": "", "label": "Stated|Inferred|Unknown",
               "sources": ["B-…"]}],
    "submission": [{"rule": "", "flag": "|MANDATORY|DISQUALIFIER", "label": "Stated", "sources": ["B-…"]}],
    "summary": {"customer": {"text": "", "sources": []}, "outcomes": {"text": "", "sources": []},
                "why_now": {"text": "", "label": "Stated|Inferred", "sources": []}, "scope": {"text": "", "sources": []},
                "fit": "High|Medium|Low", "fit_reasons": [{"text": "", "label": "Inferred", "sources": []}]},
    "findings": [{"text": "inconsistency, oddity or risk worth knowing now", "label": "Stated|Inferred", "sources": ["B-…"]}],
    "unknowns": [{"text": "needs clarification", "sources": ["B-…"]}],
    "confirms": [{"text": "", "role": "Deal Desk|Legal|Security|Product Management|…", "question": "exact question"}],
}


# ---------------------------------------------------------------- save and render
def save(deal, data, config):
    blocks = load_blocks(deal)
    problems = []
    cov = coverage.report(deal)
    if not cov["complete"]:
        problems.append(f"extraction isn't complete ({cov['total']['open']} candidate(s) open, "
                        f"{cov['total']['chunks_open']} chunk(s) to do): finish `bid extract` first")

    def src(item, where, required=True):
        ids = item.get("sources") or []
        if required and not ids:
            problems.append(f"{where}: no sources")
        bad = [i for i in ids if i not in blocks]
        if bad:
            problems.append(f"{where}: unknown block(s) {', '.join(bad)}")
        return [i for i in ids if i in blocks]

    def label(item, where, allowed=LABELS):
        if item.get("label") not in allowed:
            problems.append(f"{where}: label must be one of {', '.join(sorted(allowed))}")

    pack = {d["name"]: d for d in docs(deal)}
    listed = [d.get("file") for d in data.get("documents") or []]
    for name in pack:
        if listed.count(name) != 1:
            problems.append(f"documents: {name} must be listed exactly once")
    for d in data.get("documents") or []:
        if d.get("file") not in pack:
            problems.append(f"documents: {d.get('file')!r} is not in the pack")
            continue
        if d.get("type") not in DOC_TYPES:
            problems.append(f"documents: {d['file']}: type must be one of {', '.join(DOC_TYPES)}")
        if d.get("readable") not in ("Y", "N", "Partial"):
            problems.append(f"documents: {d['file']}: readable must be Y, N or Partial")
        elif pack[d["file"]]["unread"] and d["readable"] == "Y":
            problems.append(f"documents: {d['file']}: parts couldn't be read ({pack[d['file']]['unread'][0]['what']}), so not Y")
    for n, m in enumerate(data.get("missing") or [], 1):
        src(m, f"missing {n}")
    for n, f in enumerate(data.get("forms") or [], 1):
        src(f, f"forms {n}")
    for n, d in enumerate(data.get("dates") or [], 1):
        where = f"dates {n} ({d.get('milestone', '')})"
        ids = src(d, where)
        label(d, where)
        if not (d.get("as_written") or "").strip():
            problems.append(f"{where}: `as_written` must quote the source")
        elif ids and not R.faithful(d["as_written"], [blocks[i]["text"] for i in ids]):
            problems.append(f"{where}: `as_written` isn't in the source")
        if d.get("date"):
            try:
                dt.date.fromisoformat(d["date"])
            except ValueError:
                problems.append(f"{where}: date must be YYYY-MM-DD")
                continue
            written = set().union(*(dates_in(blocks[i]["text"]) for i in ids)) if ids else set()
            if d.get("label") == "Stated" and d["date"] not in written:
                problems.append(f"{where}: {d['date']} isn't written in the source: label it Inferred if you worked it out")
        elif d.get("label") == "Stated" and not re.search(r"tbc|tba|to be confirmed", d.get("as_written", ""), re.I):
            problems.append(f"{where}: Stated with no date: give the date, or label it Unknown")
    for n, s in enumerate(data.get("submission") or [], 1):
        src(s, f"submission {n}")
        label(s, f"submission {n}")
        if (s.get("flag") or "") not in FLAGS:
            problems.append(f"submission {n}: flag must be empty, MANDATORY or DISQUALIFIER")
    sm = data.get("summary") or {}
    for k in ("customer", "outcomes", "scope", "why_now"):
        if not (sm.get(k) or {}).get("text"):
            problems.append(f"summary.{k}: missing")
        else:
            src(sm[k], f"summary.{k}", required=k != "why_now" or sm[k].get("label") == "Stated")
    if sm.get("fit") not in ("High", "Medium", "Low"):
        problems.append("summary.fit: High, Medium or Low")
    for n, r in enumerate(sm.get("fit_reasons") or [], 1):
        label(r, f"summary.fit_reasons {n}")
    if not sm.get("fit_reasons"):
        problems.append("summary.fit_reasons: give the top reasons")
    for n, f in enumerate(data.get("findings") or [], 1):
        src(f, f"findings {n}")
        label(f, f"findings {n}")
    for n, u in enumerate(data.get("unknowns") or [], 1):
        src(u, f"unknowns {n}")
    for n, c in enumerate(data.get("confirms") or [], 1):
        if not c.get("role") or not c.get("question"):
            problems.append(f"confirms {n}: give the role and the exact question")
    if problems:
        return None, problems

    reg = registers.replace_stage(deal, "stage1",
                                  [{"kind": "U", "text": u["text"], "source": u.get("sources")} for u in data.get("unknowns") or []]
                                  + [{"kind": "C", "text": c["text"] or c["question"], "role": c["role"], "question": c["question"]}
                                     for c in data.get("confirms") or []])
    files.write(deal.path / "data" / "stage1.json", data)
    files.write(deal.path / "data" / "dates.json", {"milestones": [
        {"name": d["milestone"], "date": d["date"], "label": d["label"]} for d in data.get("dates") or [] if d.get("date")]})
    st = state.load(deal)
    prev = st["stages"].get("stage1", {})
    version = prev.get("version", 0) + 1
    out = deal.path / "stages" / "stage-1.md"
    if out.exists():
        out.rename(deal.path / "stages" / f"stage-1.v{version - 1}.md")
    out.write_text(render(deal, data, cov, reg, config, version), encoding="utf-8")
    st["stages"]["stage1"] = {"done": True, "gate_passed": False, "version": version, "saved": f"{dt.date.today():%Y-%m-%d}"}
    state.save(deal, st)
    return out, []


def render(deal, data, cov, reg_ids, config, version):
    blocks = load_blocks(deal)
    c = lambda ids: "; ".join(R.cite(blocks[i]) for i in ids or [] if i in blocks) or "—"
    bid = deal.bid()
    today = dt.date.today()
    L = [f"# Stage 1 — Inventory & understanding", "",
         f"{bid.get('customer')} · {bid.get('rfp')} · version {version} · {today:%d %b %Y}", ""]

    L += ["## 1.1 Document inventory", "", "| Document | Type | What it contains | Readable |", "|---|---|---|---|"]
    for d in data["documents"]:
        L.append(f"| {d['file']} | {d['type']} | {d['contains']} | {d['readable']} |")
    unread = [(d["name"], u) for d in docs(deal) for u in d["unread"]]
    if unread:
        L += ["", "**Not read:**"] + [f"- {n}: {u['what']} — {u['why']}" for n, u in unread]
    hidden = [(d["name"], d["stats"].get("hidden_sheets")) for d in docs(deal) if d["stats"].get("hidden_sheets")]
    if hidden:
        L += [""] + [f"- {n}: hidden sheet(s) {', '.join(h)}" for n, h in hidden]
    L += ["", "**Referenced but not in the pack:**"]
    L += [f"- {m['reference']}{' — ' + m['note'] if m.get('note') else ''} ({c(m['sources'])})" for m in data.get("missing") or []] or ["- none found"]
    L += ["", "**Forms and templates to fill:**"]
    L += [f"- {f['name']}{' — ' + f['file'] if f.get('file') else ' — **not in the pack**'} ({c(f['sources'])})"
          for f in data.get("forms") or []] or ["- none"]

    L += ["", "## 1.2 Key dates", "", "| Milestone | Date | Time & zone | As written | Label | Source |", "|---|---|---|---|---|---|"]
    for d in data.get("dates") or []:
        when = d["date"] or "—"
        if d["date"]:
            left = (dt.date.fromisoformat(d["date"]) - today).days
            when += f" ({left} days left)" if left >= 0 else " (passed)"
        tz = " ".join(x for x in (d.get("time"), d.get("timezone")) if x) or "—"
        L.append(f"| {d['milestone']} | {when} | {tz} | {d['as_written']} | {d['label']} | {c(d['sources'])} |")

    L += ["", "## 1.3 Submission requirements", ""]
    for s in data.get("submission") or []:
        flag = f"**[{s['flag']}]** " if s.get("flag") else ""
        L.append(f"- {flag}{s['rule']} — *{s['label']}* ({c(s['sources'])})")

    sm = data["summary"]
    L += ["", "## 1.4 Executive summary", "",
          f"**Customer.** {sm['customer']['text']} ({c(sm['customer'].get('sources'))})", "",
          f"**What they want.** {sm['outcomes']['text']} ({c(sm['outcomes'].get('sources'))})", "",
          f"**Why now.** {sm['why_now']['text']} — *{sm['why_now'].get('label', 'Inferred')}*"
          + (f" ({c(sm['why_now'].get('sources'))})" if sm["why_now"].get("sources") else ""), "",
          f"**Scope.** {sm['scope']['text']} ({c(sm['scope'].get('sources'))})", "",
          f"**Initial fit: {sm['fit']}**"]
    L += [f"- {r['text']} — *{r['label']}*" + (f" ({c(r.get('sources'))})" if r.get("sources") else "") for r in sm["fit_reasons"]]

    if data.get("findings"):
        L += ["", "## Findings worth knowing now", ""]
        L += [f"- {f['text']} — *{f['label']}* ({c(f['sources'])})" for f in data["findings"]]

    L += ["", "## Extraction coverage", "",
          "| Document | Blocks | Candidates | Requirements | Dismissed | Open |", "|---|---|---|---|---|---|"]
    for d in cov["docs"]:
        L.append(f"| {d['doc']} | {d['blocks']} | {d['candidates']} | {d['requirements']} | {d['dismissed']} | {d['open']} |")
    t = cov["total"]
    L.append(f"| **Total** | {t['blocks']} | {t['candidates']} | {t['requirements']} | {t['dismissed']} | {t['open']} |")
    ob = config["requirements"]["obligations"]
    L += ["", "By obligation: " + ", ".join(f"{ob.get(k, {}).get('label', k)} {v}" for k, v in cov["obligations"].items())
          + f" · added by the model beyond the code pass: {cov['added']}"]
    m = cov["matrix"]
    if m:
        L += ["", f"**Buyer's compliance matrix:** {m['linked']} of {m['rows']} rows ({m['share']:.0%}) traced to a "
              f"requirement in the RFP body. Untraced rows: {len(m['unlinked'])} ({len(m['unlinked_mandatory'])} mandatory). "
              f"RFP-body requirements not in the buyer's matrix: {len(m['body_not_in_matrix'])}."]

    regs = {i["id"]: i for i in registers.items(deal)}
    L += ["", "---", "", "**Gate checklist**",
          f"- [ ] {config['stages']['stage1'].get('gate_check', '')}",
          "- [ ] Spot-check passed (`bid spotcheck`)",
          "- [ ] Dates and submission rules checked against the RFP", "",
          "**New Unknown / Confirm items**"]
    L += [f"- {i}: {regs[i]['text']}" + (f" — ask {regs[i]['role']}: {regs[i]['question']}" if regs[i].get("role") else "")
          for i in reg_ids] or ["- none"]
    L += ["", "**Recommended next step:** pass the Stage 1 gate, then Stage 2 (qualification)."]
    return "\n".join(L) + "\n"
