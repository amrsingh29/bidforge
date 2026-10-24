"""End-to-end test: a tiny made-up RFP through intake, extraction, Stage 1 and Stage 2, in a throwaway
home and workspace. Checks that the fixed rules are enforced, not just that the happy path works.

    python tests/e2e.py      (run by `bid selftest`)
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BID = [sys.executable, str(ROOT / "cli" / "bid.py")]
failures = []

RFP = """# 1 Submission

Proposals must be submitted by email by 15 December 2026, 12:00 SGT.

The vendor must hold a current ISO 27001 certificate; bids without it will be rejected.

# 2 Requirements

The platform shall support incident, problem and change management.

The platform should offer a mobile app for approvers.

Background: Acme Bank runs 3 data centres.
"""


def run(*args, env, ok=True):
    r = subprocess.run(BID + list(args), env=env, capture_output=True, text=True)
    if (r.returncode == 0) != ok:
        failures.append(f"bid {' '.join(args)} exited {r.returncode}:\n{r.stdout}{r.stderr}")
    return r.stdout + r.stderr


def expect(cond, what):
    print(f"  {'✓' if cond else '✗'} {what}")
    if not cond:
        failures.append(what)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    cust = tmp / "ws" / "Acme Bank"
    (cust / "rfp").mkdir(parents=True)
    (cust / "rfp" / "rfp.md").write_text(RFP)
    env = {**os.environ, "BIDFORGE_HOME": str(tmp / "home")}
    run("config", "--workspace", str(tmp / "ws"), env=env)
    run("new", "Acme Bank", "--rfp", "Core ITSM", "--files", str(cust / "rfp"), env=env)
    deal = cust / "bidforge" / "core-itsm"
    work = deal / "data" / "work"
    work.mkdir(parents=True, exist_ok=True)

    print("intake and extraction")
    out = run("intake", env=env)
    expect("candidates" in out, "intake parses the pack and marks candidates")
    blocks = {b["text"][:20]: b["id"] for b in json.loads((deal / "data" / "blocks.json").read_text())}
    bid_ = lambda start: next(v for k, v in blocks.items() if k.startswith(start[:20]))
    sub, iso, itsm, mob, bg = (bid_("Proposals must be"), bid_("The vendor must hold"), bid_("The platform shall"),
                               bid_("The platform should"), bid_("Background: Acme"))
    chunk = json.loads((deal / "data" / "chunks.json").read_text())[0]["id"]

    def save(reqs, dismissed=(), ok=True):
        f = work / "k.json"
        f.write_text(json.dumps({"requirements": reqs, "dismissed": list(dismissed)}))
        return run("extract", "save", chunk, str(f), env=env, ok=ok)

    good = [{"blocks": [sub], "text": "Proposals must be submitted by email by 15 December 2026, 12:00 SGT", "type": "administrative", "obligation": "mandatory"},
            {"blocks": [iso], "text": "The vendor must hold a current ISO 27001 certificate; bids without it will be rejected", "type": "security", "obligation": "disqualifier"},
            {"blocks": [itsm], "text": "The platform shall support incident, problem and change management", "type": "functional", "obligation": "mandatory"},
            {"blocks": [mob], "text": "The platform should offer a mobile app for approvers", "type": "functional", "obligation": "desirable"}]
    out = save(good[:3], ok=False)
    expect("not accounted for" in out, "a candidate left out is refused")
    out = save(good[:3] + [{"blocks": [mob], "text": "The platform must offer offline AI agents and a 24x7 helpdesk", "type": "functional", "obligation": "mandatory"}], ok=False)
    expect("isn't traceable" in out, "wording the source doesn't say is refused")
    out = save(good)
    expect("4 requirement(s) saved" in out, "a complete, faithful chunk is saved")
    ids1 = [r["id"] for r in json.loads((deal / "data" / "requirements" / f"{chunk}.json").read_text())["items"]]
    save(good)
    ids2 = [r["id"] for r in json.loads((deal / "data" / "requirements" / f"{chunk}.json").read_text())["items"]]
    expect(ids1 == ids2, "re-saving a chunk keeps the requirement IDs")
    expect("complete" in run("coverage", env=env), "coverage report: every candidate accounted for")

    print("Stage 1")
    s1 = {"documents": [{"file": "rfp.md", "type": "main RFP", "contains": "the whole RFP", "readable": "Y"}],
          "missing": [], "forms": [],
          "dates": [{"milestone": "Submission", "as_written": "by 15 December 2026, 12:00 SGT", "date": "2026-12-16",
                     "time": "12:00", "timezone": "SGT", "label": "Stated", "sources": [sub]}],
          "submission": [{"rule": "By email", "flag": "MANDATORY", "label": "Stated", "sources": [sub]}],
          "summary": {"customer": {"text": "Acme Bank", "sources": [bg]}, "outcomes": {"text": "ITSM", "sources": [itsm]},
                      "why_now": {"text": "not stated", "label": "Unknown"}, "scope": {"text": "ITSM", "sources": [itsm]},
                      "fit": "High", "fit_reasons": [{"text": "core ITSM", "label": "Inferred"}]},
          "findings": [], "unknowns": [{"text": "Is the mobile app scored?", "sources": [mob]}], "confirms": []}
    f = work / "s1.json"
    f.write_text(json.dumps(s1))
    out = run("stage1", "save", str(f), env=env, ok=False)
    expect("isn't written in the source" in out, "a 'Stated' date that the source doesn't say is refused")
    s1["dates"][0]["date"] = "2026-12-15"
    f.write_text(json.dumps(s1))
    expect("Stage 1 saved" in run("stage1", "save", str(f), env=env), "Stage 1 saved and written up")
    expect("U-01" in (deal / "stages" / "stage-1.md").read_text(), "Unknown item registered as U-01")
    run("gate", "pass", "stage1", env=env, ok=False)
    expect(True, "Stage 1 gate refused before the spot-check")
    run("spotcheck", env=env)
    run("spotcheck", "--ok", env=env)
    expect("gate passed" in run("gate", "pass", "stage1", env=env), "Stage 1 gate passed after the spot-check")

    print("Stage 2")
    run("capture", "relationship=Weak: no meetings yet", "competitors=ServiceNow (incumbent)", env=env)
    rows = lambda scores: [{"criterion": k, "score": v, "rationale": "because", "label": "Inferred" if v else "Unknown",
                            "sources": ["capture:relationship"] if k == "relationship" else [itsm]} for k, v in scores.items()]
    keys = ["strategic_fit", "solution_fit", "competitive", "relationship", "mandatory", "commercial", "risk", "effort", "timeline"]
    item = {"text": "x", "label": "Unknown", "sources": []}
    s2 = {"context": {"current_state": item, "pains": [item], "success_criteria": [item], "stakeholders": [item], "signals": [item]},
          "evaluation": {"method": item, "concentration": item, "competitors": [{"name": "ServiceNow", "positioning": "incumbent",
                                                                                "label": "Stated", "sources": ["capture:competitors"]}]},
          "mandatory": [], "scorecard": rows({k: 4 for k in keys}),
          "decision": {"recommendation": "Bid", "conditions": []}, "unknowns": [], "confirms": []}
    f = work / "s2.json"

    def s2save(ok=True):
        f.write_text(json.dumps(s2))
        return run("stage2", "save", str(f), env=env, ok=ok)
    expect("not assessed" in s2save(ok=False), "every pass/fail requirement must be assessed")
    rid = [r for r in json.loads((deal / "data" / "requirements" / f"{chunk}.json").read_text())["items"] if r["obligation"] == "disqualifier"][0]["id"]
    s2["mandatory"] = [{"req": rid, "can_meet": "Yes", "evidence": "", "owner": "presales"}]
    s2["scorecard"] = rows({**{k: 4 for k in keys}, "budget_fit": 3})
    expect("unknown criterion" in s2save(ok=False), "an unknown scorecard criterion is refused")
    s2["scorecard"] = rows({**{k: 4 for k in keys}, "relationship": None})
    s2["decision"]["recommendation"] = "Bid"
    expect("Pending" in s2save(ok=False), "an unscored criterion forces the decision to Pending")
    s2["decision"]["recommendation"] = "Pending"
    expect("Pending" in s2save(), "a Pending Stage 2 can be saved as a draft")
    run("gate", "pass", "stage2", "--note", "AE", env=env, ok=False)
    expect(True, "Stage 2 gate refused while Pending")
    s2["scorecard"] = rows({k: 4 for k in keys})
    s2["decision"]["recommendation"] = "No-bid"
    expect("the numbers give Bid" in s2save(ok=False), "a decision against the numbers needs an override reason")
    s2["decision"]["recommendation"] = "Bid"
    out = s2save()
    expect("75.0/100" in out, "weighted score worked out by the code (all 4s = 75)")
    md = (deal / "stages" / "stage-2.md").read_text()
    expect("*(unverified)*" in md, "a Yes without evidence prints as unverified")
    run("gate", "pass", "stage2", env=env, ok=False)
    expect(True, "Stage 2 gate needs a note saying who agreed")
    run("gate", "pass", "stage2", "--note", "Agreed with Priya (AE)", env=env)
    expect("Scope & requirements" in run("status", env=env).split("Next:")[-1], "after a Bid, the next step is Stage 3")
    s2["mandatory"][0]["can_meet"] = "No"
    s2["decision"]["recommendation"] = "No-bid"
    expect("knockouts" in s2save(), "a pass/fail item we can't meet knocks the bid out")
    run("gate", "pass", "stage2", "--note", "Agreed with Priya (AE)", env=env)
    expect("No-bid" in run("status", env=env).split("Next:")[-1], "after an agreed No-bid, the analysis stops")

print()
if failures:
    print(f"✗ e2e: {len(failures)} failure(s)")
    for x in failures:
        print("  - " + x.replace("\n", "\n    "))
    sys.exit(1)
print("✓ e2e passed")
