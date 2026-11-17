"""End-to-end test for Phase 3: packs, evidence lookup, and Stages 3, 4 and 5, in a throwaway home and
workspace. Like tests/e2e.py it checks the fixed rules are enforced, not just that the happy path works —
most of these cases are a save that must be REFUSED.

    python tests/e2e_stages.py      (run by `bid selftest`)
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BID = [sys.executable, str(ROOT / "cli" / "bid.py")]
failures = []

RFP = """# 1 Submission

Proposals must be submitted by email by 15 December 2026, 12:00 SGT.

# 2 Requirements

The platform shall support incident, problem and change management.

The platform shall provide a configuration management database with discovery.

The platform shall support SSO using SAML 2.0.

The platform must monitor BMS cooling telemetry from the data hall.

The buyer requires ISO 27001 certification, and the successful vendor must allow audit of its operations.

# 3 Evaluation and contract

The solution must be evaluated on total cost of ownership.

The contract shall be governed by the laws of Singapore and liability shall be capped at 12 months of fees.
"""


def run(*args, env, ok=True):
    r = subprocess.run(BID + list(args), env=env, capture_output=True, text=True)
    if (r.returncode == 0) != ok:
        failures.append(f"bid {' '.join(args)} exited {r.returncode} (wanted {'0' if ok else 'non-zero'}):\n"
                        f"{r.stdout}{r.stderr}")
    return r.stdout + r.stderr


def expect(cond, what):
    print(f"  {'✓' if cond else '✗'} {what}")
    if not cond:
        failures.append(what)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data) if not isinstance(data, str) else data)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    cust = tmp / "ws" / "Singapore" / "Acme Bank"
    (cust / "rfp").mkdir(parents=True)
    (cust / "rfp" / "rfp.md").write_text(RFP)
    env = {**os.environ, "BIDFORGE_HOME": str(tmp / "home"), "BIDFORGE_EVIDENCE": str(tmp / "evidence")}
    lib = tmp / "evidence"
    lib.mkdir()
    (lib / "incident-management.md").write_text(
        "# Incident management\n\nThe platform supports incident and major incident management, with queues, "
        "assignment rules and work notes. See the administration guide, Incident Management chapter.\n")
    run("config", "--workspace", str(tmp / "ws"), env=env)
    run("new", "Acme Bank", "--rfp", "Core ITSM", "--files", str(cust / "rfp"), env=env)
    deal = cust / "bidforge" / "core-itsm"
    work = deal / "data" / "work"
    work.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- packs
    print("packs")
    out = run("packs", "list", env=env)
    expect("example-product" in out and "singapore" in out, "the shipped packs are listed")
    out = run("packs", "check", env=env)
    expect("every pack is valid" in out and "no source yet" in out,
           "packs check separates malformed packs from unsourced catalogue entries")
    run("packs", "use", "example-product", "singapore", "banking", env=env)
    expect("example-product" in run("status", env=env), "the deal records which packs it uses")
    out = run("packs", "use", "nope", env=env, ok=False)
    expect("no pack" in out, "an unknown pack is refused")
    out = run("packs", "check", env=env)
    expect("no `evidence`" not in out, "a deal with unsourced catalogue entries still checks clean")

    # ---------------------------------------------------------------- intake through Stage 2
    run("intake", env=env)
    blocks = {b["text"][:40]: b["id"] for b in json.loads((deal / "data" / "blocks.json").read_text())}
    bid_ = lambda s: next(v for k, v in blocks.items() if k.startswith(s[:30]))
    sub = bid_("Proposals must be submitted")
    itsm = bid_("The platform shall support incident")
    cmdb = bid_("The platform shall provide a conf")
    saml = bid_("The platform shall support SSO")
    ot = bid_("The platform must monitor BMS")
    iso = bid_("The buyer requires ISO 27001")
    tco = bid_("The solution must be evaluated")
    gov = bid_("The contract shall be governed")
    chunk = json.loads((deal / "data" / "chunks.json").read_text())[0]["id"]
    save = lambda reqs, dismissed=(): (write(work / "k.json", {"requirements": reqs, "dismissed": list(dismissed)}),
                                       run("extract", "save", chunk, str(work / "k.json"), env=env))[1]
    out = save([{"blocks": [sub], "text": "Proposals must be submitted by email by 15 December 2026, 12:00 SGT",
                 "type": "administrative", "obligation": "mandatory"},
                {"blocks": [itsm], "text": "The platform shall support incident, problem and change management",
                 "type": "functional", "obligation": "mandatory"},
                {"blocks": [cmdb], "text": "The platform shall provide a configuration management database with discovery",
                 "type": "functional", "obligation": "mandatory"},
                {"blocks": [saml], "text": "The platform shall support SSO using SAML 2.0",
                 "type": "security", "obligation": "mandatory"},
                {"blocks": [ot], "text": "The platform must monitor BMS cooling telemetry from the data hall",
                 "type": "functional", "obligation": "mandatory"},
                {"blocks": [iso], "text": "The buyer requires ISO 27001 certification, and the successful vendor must allow audit",
                 "type": "security", "obligation": "disqualifier"},
                {"blocks": [tco], "text": "The solution must be evaluated on total cost of ownership",
                 "type": "commercial", "obligation": "mandatory"},
                {"blocks": [gov], "text": "The contract shall be governed by the laws of Singapore and liability shall be capped",
                 "type": "legal", "obligation": "mandatory"}])
    expect("requirement(s) saved" in out, "the RFP extracts")
    s1 = {"documents": [{"file": "rfp.md", "type": "main RFP", "contains": "everything", "readable": "Y"}],
          "missing": [], "forms": [],
          "dates": [{"milestone": "Submission", "as_written": "by 15 December 2026, 12:00 SGT", "date": "2026-12-15",
                     "time": "12:00", "timezone": "SGT", "label": "Stated", "sources": [sub]}],
          "submission": [{"rule": "By email", "flag": "MANDATORY", "label": "Stated", "sources": [sub]}],
          "summary": {"customer": {"text": "Acme Bank", "sources": [sub]}, "outcomes": {"text": "ITSM", "sources": [itsm]},
                      "why_now": {"text": "not stated", "label": "Unknown"}, "scope": {"text": "ITSM", "sources": [itsm]},
                      "fit": "High", "fit_reasons": [{"text": "core ITSM", "label": "Inferred"}]},
          "findings": [], "unknowns": [], "confirms": []}
    write(work / "s1.json", s1)
    run("stage1", "save", str(work / "s1.json"), env=env)
    run("spotcheck", env=env); run("spotcheck", "--ok", env=env)
    run("gate", "pass", "stage1", env=env)

    item = {"text": "x", "label": "Unknown", "sources": []}
    keys = ["strategic_fit", "solution_fit", "competitive", "relationship", "mandatory", "commercial",
            "risk", "effort", "timeline"]
    s2 = {"context": {k: (item if k not in ("pains", "success_criteria", "stakeholders", "signals") else [item])
                      for k in ("current_state", "pains", "success_criteria", "stakeholders", "signals")},
          "evaluation": {"method": item, "concentration": item, "competitors": []},
          "mandatory": [{"req": next(r["id"] for r in json.loads((deal / "data" / "requirements" / f"{chunk}.json")
                                                                  .read_text())["items"] if r["obligation"] == "disqualifier"),
                         "can_meet": "Yes", "evidence": "a certificate", "owner": "presales"}],
          "scorecard": [{"criterion": k, "score": 4, "rationale": "because", "label": "Inferred", "sources": [itsm]}
                        for k in keys],
          "decision": {"recommendation": "Bid", "conditions": []}, "unknowns": [], "confirms": []}
    write(work / "s2.json", s2)
    run("capture", "relationship=Weak", env=env)
    run("stage2", "save", str(work / "s2.json"), env=env)
    run("gate", "pass", "stage2", "--note", "Agreed with AE", env=env)
    reqs = {r["text"][:40]: r["id"] for r in json.loads((deal / "data" / "requirements" / f"{chunk}.json").read_text())["items"]}
    R = lambda s: next(v for k, v in reqs.items() if k.startswith(s[:30]))
    # distinct prefixes: "The platform shall sup…" would match both the ITSM and the SSO requirement
    R_ITSM, R_CMDB, R_SAML, R_OT = (R("The platform shall support incident"), R("The platform shall provide a conf"),
                                    R("The platform shall support SSO"), R("The platform must monitor BMS"))
    R_TCO, R_GOV = R("The solution must be evaluated"), R("The contract shall be governed")
    R_SUB, R_ISO = R("Proposals must be submitted"), R("The buyer requires ISO 27001")

    # ---------------------------------------------------------------- evidence
    print("evidence library")
    out = run("evidence", "list", env=env)
    expect("incident-management.md" in out, "the evidence library lists its files")
    out = run("evidence", "find", "incident management queues assignment", env=env)
    expect("library" in out and "incident-management" in out, "a topic finds the library entry")
    out = run("evidence", "find", "quantum annealing for container ships", env=env)
    expect("unverified" in out, "a topic with no source says so instead of guessing")
    run("evidence", "record", "iso=ISO 27001 certificate held, expires 2027-06-30", env=env)
    expect("iso" in run("evidence", "list", env=env), "a confirmation is recorded against the deal")

    # ---------------------------------------------------------------- Stage 3
    print("Stage 3 — scope & requirements")
    out = run("stage3", "brief", env=env)
    expect("Scope overview" in out and "Requirements" in out, "the scope brief groups requirements by domain")
    write(work / "s3scope.json", {"domains": {"service_desk": {"note": "ITSM core"},
                                             "operations": {"note": "CMDB and discovery"},
                                             "platform": {"note": "SSO, events and monitoring"},
                                             "unassigned": {"note": "submission, certification, evaluation and contract terms"}},
                                  "out_of_scope": [{"text": "OT monitoring is out of product scope", "sources": [ot]}],
                                  "statistics": {}})
    out = run("stage3", "save", str(work / "s3scope.json"), env=env)
    expect("scope" in out, "the scope overview saves")
    out = run("stage3", "brief", "--domain", "service_desk", env=env)
    expect("incident-management.md" in out, "the domain brief shows what the evidence library already has")
    expect("NO SOURCE YET" in out, "an unsourced catalogue module is flagged before rating")

    def rate(dom, rows, extra=None, ok=True):
        d = {"domain": dom, "ratings": rows, "unknowns": [], "confirms": []}
        d.update(extra or {})
        write(work / "s3.json", d)
        return run("stage3", "save", str(work / "s3.json"), env=env, ok=ok)

    # a rating whose evidence doesn't exist must be refused
    out = rate("service_desk", [{"req": R_ITSM, "level": "complies", "module": "module_service_desk",
                             "evidence": [{"kind": "library", "cite": "nowhere.md"}]}], ok=False)
    expect("not a block, requirement" in out, "evidence that doesn't exist is refused")
    # a module that isn't in the pack must be refused
    out = rate("service_desk", [{"req": R_ITSM, "level": "complies", "module": "magic_module",
                             "evidence": [{"kind": "library", "cite": "incident-management.md"}]}], ok=False)
    expect("isn't in the pack catalogue" in out, "an invented module is refused")
    # a level outside the configuration must be refused
    out = rate("service_desk", [{"req": R_ITSM, "level": "totally fine", "module": "module_service_desk",
                             "evidence": [{"kind": "library", "cite": "incident-management.md"}]}], ok=False)
    expect("is not one of" in out, "a level the configuration doesn't define is refused")
    # a gap without what_fails must be refused, because Stage 4 can't mitigate it
    out = rate("operations", [{"req": R_CMDB, "level": "partial", "module": "module_service_desk",
                          "evidence": [{"kind": "library", "cite": "incident-management.md"}]}], ok=False)
    expect("what we can't meet" in out, "a gap has to say what fails")
    # a partial domain is a draft, not a completion
    out = rate("operations", [{"req": R_CMDB, "level": "partial", "module": "module_service_desk",
                          "evidence": [{"kind": "library", "cite": "incident-management.md"}],
                          "what_fails": "no automated reconciliation"}], extra={"partial": True})
    expect("rated" in out, "a partial domain saves as a draft")
    expect("not complete" in run("stage3", "matrix", env=env, ok=False), "the matrix reports itself incomplete")
    out = run("gate", "pass", "stage3", env=env, ok=False)
    expect("can't pass the Stage 3 gate" in out, "the Stage 3 gate refuses an incomplete matrix")

    # finish every domain
    rate("service_desk", [{"req": R_ITSM, "level": "complies", "module": "module_service_desk",
                       "evidence": [{"kind": "library", "cite": "incident-management.md"}]}])
    rate("operations", [{"req": R_CMDB, "level": "partial", "module": "module_service_desk",
                         "evidence": [{"kind": "library", "cite": "incident-management.md"}],
                         "what_fails": "no automated reconciliation"},
                        {"req": R_OT, "level": "non_compliant", "module": "module_operations",
                         "evidence": [{"kind": "confirmation", "cite": "confirm:iso"}],
                         "what_fails": "OT telemetry is outside product scope (rule no-adjacent-market-claim)"}])
    rate("platform", [{"req": R_SAML, "level": "complies", "module": "module_platform",
                       "evidence": [{"kind": "pack", "cite": "pack:module_platform"}]}])
    m = run("stage3", "matrix", env=env, ok=False)
    expect("unverified 1" in m, "a rating resting on an unsourced catalogue entry counts as unverified")
    out = run("gate", "pass", "stage3", env=env, ok=False)
    expect("unverified" in out, "the Stage 3 gate refuses to pass over an unverified rating")
    run("evidence", "record", "saml=SAML 2.0 SSO is supported, confirmed in the 24.x admin guide", env=env)
    rate("platform", [{"req": R_SAML, "level": "complies", "module": "module_platform",
                       "evidence": [{"kind": "confirmation", "cite": "confirm:saml"}]}])
    m = run("stage3", "matrix", env=env, ok=False)
    expect("unverified 0" in m, "sourcing the rating clears it from the unverified count")
    # the requirements that fit no product domain: they still get rated, or they were dropped (rule 5)
    out = rate("unassigned", [{"req": R_GOV, "level": "complies", "evidence": [{"kind": "confirmation", "cite": "confirm:iso"}]},
                              {"req": R_TCO, "level": "partial", "evidence": [{"kind": "confirmation", "cite": "confirm:iso"}],
                               "what_fails": "TCO model depends on pricing not yet available"}], ok=False)
    expect("not rated" in out, "a domain part-rated is refused unless it is a draft")
    rate("unassigned", [{"req": R_GOV, "level": "complies", "evidence": [{"kind": "confirmation", "cite": "confirm:iso"}]},
                        {"req": R_TCO, "level": "partial", "evidence": [{"kind": "confirmation", "cite": "confirm:iso"}],
                         "what_fails": "TCO model depends on pricing not yet available"},
                        {"req": R_SUB, "level": "complies", "evidence": [{"kind": "confirmation", "cite": "confirm:iso"}]},
                        {"req": R_ISO, "level": "complies", "evidence": [{"kind": "confirmation", "cite": "confirm:iso"}]}])
    out = run("stage3", "render", env=env)
    expect("Stage 3 written" in out, "the matrix renders once complete")
    md = (deal / "stages" / "stage-3.md").read_text()
    expect("Compliance matrix" in md and "Fit at a glance" in md, "stage-3.md has the matrix and the fit summary")
    expect("Non-functional requirements" in md, "the NFR table is there")
    expect("OT telemetry is outside product scope" in md, "the gap's reason is carried into the document")

    # ---------------------------------------------------------------- Stage 4
    print("Stage 4 — solution & licensing")
    out = run("stage4", "brief", env=env)
    expect("Gaps to mitigate" in out and "Licensing inputs" in out, "the Stage 4 brief shows gaps and the inputs to ask for")
    mods = [{"module": "module_service_desk", "why": "core ITSM and the CMDB", "reqs": [R_ITSM, R_CMDB]},
            {"module": "module_platform", "why": "SSO and events", "reqs": [R_SAML]},
            {"module": "module_operations", "why": "events and monitoring", "reqs": [R_OT]}]
    arch = {k: {"text": f"{k} description", "sources": [itsm]} for k in
            ("tenant_and_hosting", "components", "integrations", "data_flow", "environments", "non_functional_posture")}
    inputs = {"licensing": [{"key": "licensing_model", "value": "named user, per the price book", "by": "Deal Desk",
                             "role": "deal_desk"}],
              "sizing": [{"key": "user_population", "value": "1,900 employees, 60 agents", "by": "AE", "role": "presales"}],
              "services": [{"key": "implementation_scope", "value": "M (10-30 days)", "by": "PS",
                            "role": "professional_services"}],
              "confirms": [{"text": k, "role": r, "question": q} for k, r, q in [
                  ("licence_metric_per_module", "deal_desk", "What is the licence metric per module in scope?"),
                  ("quantity_basis", "deal_desk", "What drives the quantity?"),
                  ("bundle_alternatives", "deal_desk", "Which bundles cover this scope?"),
                  ("support_tier", "deal_desk", "Which support tier is proposed?"),
                  ("ticket_volume", "presales", "Ticket volume per month?"),
                  ("ci_count", "presales", "How many CIs?"),
                  ("integration_count", "presales", "How many integrations?"),
                  ("data_volume", "presales", "What data is migrated?"),
                  ("availability_target", "presales", "Availability target?"),
                  ("data_migration", "professional_services", "What data is migrated?"),
                  ("integrations_build", "professional_services", "Which integrations are built?"),
                  ("training", "professional_services", "Who is trained?"),
                  ("hypercare", "professional_services", "Hypercare length?"),
                  ("partner_split", "professional_services", "What is the partner split?")]]}
    base_mitigations = [{"req": R_CMDB, "how": "configure", "detail": "manual reconciliation with the discovery job",
                         "owner": "solution_consultant"},
                        {"req": R_OT, "how": "partner", "detail": "partner supplies the OT layer; the pack's "
                         "no-adjacent-market-claim rule keeps the claim off product", "owner": "partner"},
                        {"req": R_TCO, "how": "clarify", "detail": "ask the buyer which cost lines the TCO model "
                         "must include", "owner": "presales"}]
    s4 = {"modules": mods, "architecture": arch, "mitigations": base_mitigations,
          "integrations": [{"system": "ADFS", "direction": "inbound", "how": "SAML 2.0", "sources": [saml]}],
          "unknowns": [], **inputs}

    # inputs missing: refused, and every question named
    s4_noinputs = {k: ([] if k in ("licensing", "sizing", "services") else v) for k, v in s4.items()}
    s4_noinputs["confirms"] = []
    write(work / "s4.json", s4_noinputs)
    out = run("stage4", "save", str(work / "s4.json"), env=env, ok=False)
    expect("neither recorded nor raised as a Confirm" in out,
           "every licensing, sizing and services input is answered or asked")
    expect("scope rule" not in out, "…and the input check doesn't hide behind another problem")

    # a module nothing is rated against: refused
    # a module that exists in the catalogue but which Stage 3 never rated anything against: refused
    s4_bad = {**s4, "modules": mods + [{"module": "module_reporting", "why": "reporting", "reqs": [R_GOV]}]}
    write(work / "s4.json", s4_bad)
    out = run("stage4", "save", str(work / "s4.json"), env=env, ok=False)
    expect("no Stage 3 requirement is rated against it" in out, "a module nothing is rated against is refused")

    # an invented module key: refused
    s4_bad = {**s4, "modules": mods + [{"module": "hyper_agent", "why": "x", "reqs": [R_ITSM]}]}
    write(work / "s4.json", s4_bad)
    expect("isn't in the pack catalogue" in run("stage4", "save", str(work / "s4.json"), env=env, ok=False),
           "an invented module is refused at Stage 4 too")

    # an OT claim with no partner mitigation: refused by the pack's scope rule
    s4_ot = {**s4, "mitigations": [base_mitigations[0], base_mitigations[2]],
             "architecture": {**arch, "components": {"text": "Monitors BMS cooling telemetry via DCIM.",
                                                     "sources": [itsm]}}}
    write(work / "s4.json", s4_ot)
    out = run("stage4", "save", str(work / "s4.json"), env=env, ok=False)
    expect("scope rule no-adjacent-market-claim" in out, "an OT claim is refused by the product pack's scope rule")
    expect("gap(s) with no mitigation" in out, "…and the unmitigated gap is still reported")

    # a roadmap mitigation is never a closure
    s4_rm = {**s4, "mitigations": [base_mitigations[0], {**base_mitigations[1], "how": "roadmap"},
                                    base_mitigations[2]]}
    write(work / "s4.json", s4_rm)
    out = run("stage4", "save", str(work / "s4.json"), env=env)
    expect("still open 2" in out, "a roadmap mitigation saves but never closes the gap "
                                 "(nor does a clarification: both are `closes_it: false`)")
    out = run("gate", "pass", "stage4", env=env, ok=False)
    expect("stay open after mitigation" in out, "the Stage 4 gate refuses an open gap without a note")

    # now a clean save
    write(work / "s4.json", s4)
    out = run("stage4", "save", str(work / "s4.json"), env=env)
    expect("Stage 4 saved" in out, "a complete Stage 4 saves")
    md = (deal / "stages" / "stage-4.md").read_text()
    expect("ROADMAP RISK" not in md, "no roadmap claim was made")
    out = run("gate", "pass", "stage4", env=env, ok=False)
    expect("stay open after mitigation" in out, "the Stage 4 gate refuses while gaps stay open")
    out = run("gate", "pass", "stage4", "--note", "Open gaps accepted by the AE, 17 Nov", env=env)
    expect("gate passed" in out, "the Stage 4 gate passes once the open gaps are accepted in writing")
    out = run("stage4", "inputs", env=env)
    expect("recorded" in out, "the inputs report what is recorded and what is missing")

    # ---------------------------------------------------------------- Stage 5
    print("Stage 5 — security, compliance & legal")
    out = run("stage5", "brief", env=env)
    expect("Standing items" in out, "the standing security items are always asked")
    expect("MAS" in out and "PDPA" in out, "the Singapore pack's regulations are checked against the RFP")
    expect("AI checks" in out, "the AI section appears")
    s5 = {"security": [], "standing": [], "certifications": [], "regulations": [], "ai_trigger": "",
          "ai": [], "legal": [], "clauses": [], "handovers": [], "unknowns": [], "confirms": []}
    write(work / "s5.json", s5)
    out = run("stage5", "save", str(work / "s5.json"), env=env, ok=False)
    expect("security requirement(s) not answered" in out, "every security requirement must be answered")
    expect("standing items not covered" in out, "every standing item must be covered")
    expect("regulations not assessed" in out, "every pack regulation must be assessed")
    expect("`ai_trigger`" in out, "an untriggered AI section still needs a reason")

    sec_reqs = [r["id"] for r in json.loads((deal / "data" / "requirements" / f"{chunk}.json").read_text())["items"]
                if r["type"] == "security"]
    legal_reqs = [r["id"] for r in json.loads((deal / "data" / "requirements" / f"{chunk}.json").read_text())["items"]
                  if r["type"] == "legal"]
    # every security requirement, not a sample
    s5["security"] = [{"req": rid, "answer": "Yes", "evidence": "confirm:iso", "note": "",
                       "owner": "security", "due": "2026-12-01"} for rid in sec_reqs]
    s5["standing"] = [{"key": i, "answer": "Yes", "evidence": "confirm:iso", "owner": "security", "due": "2026-12-01"}
                      for i in ["data_residency", "access_control", "encryption", "audit_logging",
                                "certification_evidence", "penetration_test", "vulnerability", "bcp_dr",
                                "incident_notification", "subcontractors", "audit_rights", "exit"]]
    s5["certifications"] = [{"name": "ISO 27001", "claimed": "Yes", "evidence": "confirm:iso", "note": ""}]
    # every regulation the chosen packs list, taken from the packs themselves (not hard-coded)
    sys.path.insert(0, str(ROOT))
    from core import packs as _P
    regs = _P.regulations([_P.get(i) for i in ("example-product", "singapore", "banking")])
    s5["regulations"] = [{"name": r["name"], "pack": r["pack"], "applies": "Not mentioned", "sources": [gov],
                          "requirement": "", "owner": "security", "due": "2026-12-01"} for r in regs]
    s5["ai_trigger"] = "no AI in the pack or the solution"
    s5["legal"] = [{"req": legal_reqs[0], "answer": "Accept with a 12-month cap", "owner": "legal", "due": "2026-12-01"}]
    s5["clauses"] = [{"key": k, "found": "not in the pack", "risk": "unknown", "sources": [gov],
                      "position": "to be confirmed with Legal", "owner": "legal", "due": "2026-12-01"}
                     for k in ["liability", "indemnity", "sla_credits", "termination", "ip_ownership",
                               "payment_terms", "variation", "confidentiality", "data_protection", "audit",
                               "governing_law", "insurance", "flow_down", "benchmarking"]]
    write(work / "s5.json", s5)
    out = run("stage5", "save", str(work / "s5.json"), env=env)
    expect("Stage 5 saved" in out, "a complete Stage 5 saves")
    md = (deal / "stages" / "stage-5.md").read_text()
    expect("Clause risk table" in md and "Regulatory & data residency" in md, "stage-5.md has the clause table and the regulation table")
    out = run("gate", "pass", "stage5", env=env, ok=False)
    expect("unacceptable as written" in out, "the Stage 5 gate demands Legal's position on high-risk clauses")
    out = run("gate", "pass", "stage5", "--note", "Legal accepts as a position to negotiate", env=env)
    expect("gate passed" in out, "the Stage 5 gate passes once Legal's position is recorded")

    # a certification claimed without a source is refused
    s5["certifications"] = [{"name": "SOC 2", "claimed": "Yes", "evidence": "", "note": ""}]
    write(work / "s5.json", s5)
    out = run("stage5", "save", str(work / "s5.json"), env=env, ok=False)
    expect("no evidence" in out, "a certification claimed with no certificate is refused")

    print()
    out = run("status", env=env)
    marked = [ln for ln in out.splitlines() if "not built yet" in ln]
    expect(not any(f"{n}. " in ln for n in (3, 4, 5) for ln in marked),
           "status no longer marks Stages 3-5 as unbuilt")
    expect(any("Roles, risks" in ln for ln in marked), "…and still marks 6-7 as unbuilt, honestly")
    expect("Roles, risks & clarifications" in out.split("Next:")[-1], "after Stage 5 the next step is Stage 6")

print()
if failures:
    print(f"✗ e2e stages: {len(failures)} failure(s)")
    for x in failures:
        print("  - " + x.replace("\n", "\n    "))
    sys.exit(1)
print("✓ e2e stages passed")
