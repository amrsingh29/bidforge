#!/usr/bin/env python3
"""BidForge CLI: reads an RFP pack and runs the staged bid analysis. The /bid skill drives it.

  bid new "<customer>" --rfp "<name>" [--files F...] [--folder DIR] [--parent Country] [--pick N]
                                     start a deal in the customer's folder and make it current
  bid where "<customer>" [--create --parent Country] [--pick N] [--folder DIR]   find (or pin) a customer folder
  bid list | use <deal>              known deals; switch the current one
  bid status [--deal D]              stages, gates, team, open items, deadlines, and the next step
  bid pack add F... [--deal D]       add files (or a folder) to the RFP pack
  bid team [role=person ...] [--deal D]   show or name the people on this bid (role= clears)
  bid config [--workspace P] [--customer-path auto|PATTERN] [--subfolder N]   show or set your settings
  bid config show [ID] [--deal D]    effective configuration, and which layer set each value
  bid config check [--deal D]        catch typos, broken stages, roles that don't exist
  bid intake [--force | --remark]    parse the pack, mark candidate requirements, cut the model's chunks
                                     (--remark: mark candidates again, keeping blocks and finished chunks)
  bid extract next | show K-NN | save K-NN FILE.json   the model pass, one chunk at a time
  bid coverage                       per document: candidates, requirements, dismissed, open; buyer matrix
  bid spotcheck [--ok | --issues "what's wrong"]   a varied sample to check against the source
  bid stage1 brief | save FILE.json  Stage 1 inventory, dates, submission rules, summary
  bid capture [KEY="answer" ...]     what the pack can't tell us (relationship, competitors…); KEY= clears
  bid stage2 brief | save FILE.json  Stage 2 qualification: context, pass/fail items, scorecard, decision
  bid gate pass STAGE [--note "..."] record that you passed a hard gate (only on your say-so)
  bid doctor                         check the install
  bid selftest                       run the self-test in a throwaway home and workspace

Settings and your personal profile live in ~/.bidforge (BIDFORGE_HOME overrides).
"""
import argparse, datetime as dt, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import evidence, packs as P                                   # noqa: E402
from core import settings                                               # noqa: E402
from core.config import layers                                          # noqa: E402
from core.deal import workspace as ws                                   # noqa: E402
from core.deal.deal import Deal, DealError, deal_base                   # noqa: E402
from core.paths import PROFILE                                          # noqa: E402
from core.intake import coverage                                        # noqa: E402
from core.intake.run import IntakeError, chunks, intake, remark                # noqa: E402
from core.stages import stage1, stage2, stage3, stage4, stage5          # noqa: E402
from core.store import capture                                          # noqa: E402
from core.store import registers, state                                 # noqa: E402
from core.store import requirements as R                                # noqa: E402

# Stages whose engine exists. Grows phase by phase (PLAN.md); the skill never pretends otherwise.
BUILT = {"stage1", "stage2", "stage3", "stage4", "stage5"}


def fail(msg):
    sys.exit(f"✗ {msg}")


def deal_arg(a):
    try:
        return Deal.find(a.deal) if getattr(a, "deal", None) else Deal.current()
    except DealError as e:
        fail(e)


# ---------------------------------------------------------------- deals
def cmd_new(a):
    try:
        base = deal_base(a.customer, a.folder, a.pick, a.parent)
        deal = Deal.create(base, a.customer, a.rfp, a.files or ())
    except ws.Ambiguous as e:
        fail(f"{e}:\n" + "\n".join(f"    {i}. {p}" for i, p in enumerate(e.candidates, 1))
             + "\n  choose with --pick N, or give the folder with --folder DIR")
    except (ws.NotFound, DealError) as e:
        fail(f"{e}\n  give the folder with --folder DIR, or create it with --parent Country (\"\" for flat)")
    print(f"✓ deal {deal.slug} (now current)\n  folder: {deal.path}\n  pack:   {len(deal.pack())} file(s)")
    if ws.workspace() is None:
        print("  note: no workspace set, so the deal is in BidForge's deals/ (bid config --workspace PATH)")


def cmd_where(a):
    try:
        if a.folder:
            folder = ws.remember(a.customer, a.folder)
        else:
            try:
                folder = ws.resolve(a.customer, a.pick)
            except ws.NotFound:
                if not a.create:
                    raise
                folder = ws.create(a.customer, a.parent or "")
    except ws.Ambiguous as e:
        fail(f"{e}:\n" + "\n".join(f"    {i}. {p}" for i, p in enumerate(e.candidates, 1)) + "\n  choose with --pick N")
    except ws.NotFound as e:
        fail(e)
    print(f"customer folder: {folder}\nBidForge folder: {folder / settings.get('subfolder')}")


def cmd_list(a):
    known, cur = settings.load().get("deals") or {}, settings.load().get("current")
    if not known:
        print("no deals yet (bid new)")
    for s, p in known.items():
        print(f"{'*' if s == cur else ' '} {s:40} {p}{'' if Path(p, 'bid.yaml').exists() else '   (missing)'}")


def cmd_use(a):
    try:
        deal = Deal.find(a.name)
    except DealError as e:
        fail(e)
    settings.save(current=deal.slug)
    print(f"✓ current deal: {deal.slug}")


def cmd_pack(a):
    deal = deal_arg(a)
    try:
        added = deal.add_files(a.files)
    except DealError as e:
        fail(e)
    print(f"✓ {len(added)} file(s) added; pack has {len(deal.pack())}")


def cmd_team(a):
    deal = deal_arg(a)
    bid = deal.bid()
    team = bid.get("team") or {}
    if a.assign:
        config, _ = layers.effective(deal)
        roles = config.get("roles") or {}
        for kv in a.assign:
            role, _, people = kv.partition("=")
            if role not in roles:
                fail(f"`{role}` is not a role. Roles: {', '.join(roles)}")
            names = [p.strip() for p in people.split(",") if p.strip()]
            if names:
                team[role] = names[0] if len(names) == 1 else names
            else:
                team.pop(role, None)
        bid["team"] = team
        deal.save_bid(bid)
    print_team(deal, team)


def print_team(deal, team):
    config, _ = layers.effective(deal)
    roles = {k: v for k, v in (config.get("roles") or {}).items() if v.get("enabled", True)}
    if not team:
        print("team: no one named yet (bid team presales=NAME sales=NAME ...)")
        return
    print("team:")
    for role, people in team.items():
        label = roles.get(role, {}).get("label", role)
        names = ", ".join(people) if isinstance(people, list) else str(people)
        print(f"  {label:34} {names}")


# ---------------------------------------------------------------- status
def cmd_status(a):
    deal = deal_arg(a)
    bid = deal.bid()
    config, _ = layers.effective(deal)
    st = state.load(deal)
    print(f"Deal:   {bid.get('customer')} — {bid.get('rfp')}   ({deal.slug})\nFolder: {deal.path}")
    print(f"Pack:   {len(deal.pack())} file(s)" + ("" if deal.pack() else "  (bid pack add FILES)"))
    print(f"Packs:  {', '.join(bid.get('packs') or []) or 'none yet (suggested at Stage 1)'}")
    print_team(deal, bid.get("team") or {})
    dates = state.deadlines(deal)
    if not dates:
        print("Key dates: not extracted yet (Stage 1)")
    else:
        print("Key dates:")
        today = dt.date.today()
        for m in dates:
            left = (dt.date.fromisoformat(m["date"]) - today).days
            print(f"  {m['name']:34} {m['date']}  ({left} day(s) left)" if left >= 0 else f"  {m['name']:34} {m['date']}  (passed)")
    reg = state.registers(deal)
    print(f"Open items: {reg['U']} Unknown · {reg['C']} Confirm")
    print("Stages:")
    for i, (sid, s) in enumerate(layers.ordered_stages(config), 1):
        built = "" if sid in BUILT else "  (not built yet)"
        print(f"  {i}. {s['name']:34} {state.stage_status(st, sid):16} {s['gate']} gate{built}")
    kind, sid, s = state.next_step(deal, config)
    if kind == "stopped":
        print("Next:   nothing: the bid decision was No-bid (stages/stage-2.md has the rationale)")
    elif kind == "finished":
        print("Next:   all stages done (bid export)")
    elif kind == "gate":
        print(f"Next:   waiting for you at the {s['name']} gate: {s.get('gate_check', '')}")
    else:
        print(f"Next:   {s['name']}" + ("" if sid in BUILT else " — not built yet (PLAN.md phases)"))
    problems = layers.check(deal)
    if problems:
        print(f"⚠ configuration: {len(problems)} problem(s) (bid config check)")


# ---------------------------------------------------------------- intake and extraction
def cmd_intake(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    if a.remark:
        try:
            r = remark(deal, config)
        except IntakeError as e:
            fail(e)
        print(f"✓ {r['candidates']} candidates; chunk(s) back to do: {', '.join(r['reopened']) or 'none'}")
        return
    try:
        r = intake(deal, config, a.force)
    except IntakeError as e:
        fail(e)
    if r.get("unchanged"):
        print("pack unchanged since the last intake: nothing to do (bid extract next)")
        return
    for d in r["docs"]:
        print(f"  {d['name'][:56]:56} {d['blocks']:5} blocks {d['candidates']:5} candidates"
              + ("  [buyer compliance matrix]" if d["matrix"] else ""))
        for u in d["unread"]:
            print(f"      ⚠ not read: {u['what']} — {u['why']}")
        if d["stats"].get("hidden_sheets"):
            print(f"      ⚠ hidden sheet(s): {', '.join(d['stats']['hidden_sheets'])}")
    pending = sum(1 for c in chunks(deal) if c["status"] == "pending")
    print(f"✓ {r['blocks']} blocks, {r['candidates']} candidates, {r['chunks']} chunks ({pending} for the model pass)")


def cmd_extract(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    if not chunks(deal):
        fail("no intake yet (bid intake)")
    if a.action == "next":
        todo = [c for c in chunks(deal) if c["status"] == "pending"]
        if not todo:
            print("all chunks done (bid coverage)")
            return
        print(f"{len(todo)} chunk(s) to do.\n")
        print(R.render_chunk(deal, todo[0]["id"], config))
    elif a.action == "show":
        try:
            print(R.render_chunk(deal, a.chunk, config))
        except KeyError as e:
            fail(e.args[0])
    elif a.action == "save":
        if not a.chunk or not a.file:
            fail("bid extract save K-NN FILE.json")
        try:
            data = json.loads(Path(a.file).read_text())
            saved, problems = R.save_chunk(deal, a.chunk, data, config)
        except (OSError, json.JSONDecodeError, KeyError) as e:
            fail(f"can't read {a.file}: {e}")
        if problems:
            print(f"✗ chunk {a.chunk} not saved:\n" + "\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        left = sum(1 for c in chunks(deal) if c["status"] == "pending")
        print(f"✓ {a.chunk}: {len(saved)} requirement(s) saved; {left} chunk(s) left")
    else:
        fail("bid extract next | show K-NN | save K-NN FILE.json")


def cmd_coverage(a):
    deal = deal_arg(a)
    cov = coverage.report(deal)
    print(f"{'document':56} blocks  cand  reqs  dism  open")
    for d in cov["docs"]:
        print(f"{d['doc'][:56]:56} {d['blocks']:6} {d['candidates']:5} {d['requirements']:5} {d['dismissed']:5} {d['open']:5}"
              + (f"  ({d['chunks_open']} chunk(s) to do)" if d["chunks_open"] else ""))
        for u in d["unread"]:
            print(f"    ⚠ not read: {u['what']} — {u['why']}")
    t = cov["total"]
    print(f"{'TOTAL':56} {t['blocks']:6} {t['candidates']:5} {t['requirements']:5} {t['dismissed']:5} {t['open']:5}")
    print(f"by obligation: {cov['obligations']} · by type: {cov['types']} · added beyond the code pass: {cov['added']}")
    m = cov["matrix"]
    if m:
        print(f"buyer matrix: {m['linked']}/{m['rows']} rows ({m['share']:.0%}) traced to the RFP body; "
              f"untraced {len(m['unlinked'])} ({len(m['unlinked_mandatory'])} mandatory); "
              f"body requirements not in the matrix: {len(m['body_not_in_matrix'])}; section mismatches: {len(m['section_mismatch'])}")
    print("✓ complete: every candidate accounted for" if cov["complete"] else "✗ not complete yet")
    (deal.path / "data" / "coverage.json").write_text(json.dumps(cov, indent=1) + "\n")


def cmd_spotcheck(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    p = deal.path / "data" / "spotcheck.json"
    if a.ok or a.issues:
        if not p.exists():
            fail("show the sample first (bid spotcheck)")
        rec = json.loads(p.read_text())
        rec.update({"status": "ok" if a.ok else "issues", "note": a.issues or "", "checked": f"{dt.date.today():%Y-%m-%d}"})
        p.write_text(json.dumps(rec, indent=1) + "\n")
        print("✓ spot-check recorded as passed" if a.ok else "✓ issues recorded: fix them (bid extract show K-NN, then save), then re-check")
        return
    if not coverage.report(deal)["complete"]:
        fail("extraction isn't complete yet (bid coverage)")
    from core.intake.run import load_blocks
    blocks = load_blocks(deal)
    sample = coverage.spot_sample(deal, config["requirements"]["spot_check"]["sample"])
    p.write_text(json.dumps({"sample": [s["id"] for s in sample], "status": "pending"}, indent=1) + "\n")
    ob = config["requirements"]["obligations"]
    for s in sample:
        if s["id"].startswith("dismissed:"):
            print(f"\n■ DISMISSED ({s['chunk']}): {s['reason']}")
        else:
            print(f"\n■ {s['id']} [{ob[s['obligation']]['label']}] [{s['type']}] ({s['chunk']}, {s['via']}): {s['text']}")
        for b in s["blocks"]:
            print(f"    source {R.cite(blocks[b])}:\n      \"{blocks[b]['text'][:600]}\"")
    print("\nCheck each against its source. Then: bid spotcheck --ok, or --issues \"what's wrong\"")


def cmd_stage1(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    if a.action == "brief":
        if not chunks(deal):
            fail("no intake yet (bid intake)")
        print(stage1.brief(deal))
    elif a.action == "save":
        if not a.file:
            fail("bid stage1 save FILE.json")
        try:
            data = json.loads(Path(a.file).read_text())
        except (OSError, json.JSONDecodeError) as e:
            fail(f"can't read {a.file}: {e}")
        out, problems = stage1.save(deal, data, config)
        if problems:
            print("✗ Stage 1 not saved:\n" + "\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        print(f"✓ Stage 1 saved: {out}")
    else:
        fail("bid stage1 brief | save FILE.json")


def cmd_capture(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    asked = config["qualification"]["capture"]
    for kv in a.assign or []:
        key, _, value = kv.partition("=")
        if key not in asked:
            fail(f"`{key}` is not a capture input. Inputs: {', '.join(asked)} (add your own in your profile)")
        capture.set_(deal, key, value)
    have = capture.load(deal)
    for k, question in asked.items():
        print(f"  {k:13} " + (f"{have[k]['value']}  ({have[k]['by']}, {have[k]['date']})" if k in have else f"— {question}"))


def cmd_stage2(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    if a.action == "brief":
        print(stage2.brief(deal, config))
    elif a.action == "save":
        if not a.file:
            fail("bid stage2 save FILE.json")
        try:
            data = json.loads(Path(a.file).read_text())
        except (OSError, json.JSONDecodeError) as e:
            fail(f"can't read {a.file}: {e}")
        out, problems = stage2.save(deal, data, config)
        if problems:
            print("✗ Stage 2 not saved:\n" + "\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        n = stage2.score(data, config)
        print(f"✓ Stage 2 saved: {out}\n  recommendation: {data['decision']['recommendation']} · score {n['total']}/100"
              + (f" · pending: {', '.join(n['pending'])}" if n["pending"] else "")
              + (f" · knockouts: {', '.join(n['knockouts'])}" if n["knockouts"] else ""))
    else:
        fail("bid stage2 brief | save FILE.json")


# ---------------------------------------------------------------- packs and evidence
def cmd_packs(a):
    all_ = P.available()
    if a.action in (None, "list"):
        if not all_:
            print("no packs installed (packs/products, packs/regions, packs/industries)")
            return
        deal = None
        if settings.load().get("current"):
            try:
                deal = Deal.current()
            except DealError:
                deal = None
        chosen = set(P.selected(deal)) if deal else set()
        print(f"{'':2} {'id':22} {'type':9} {'version':8} label")
        for pid, p in sorted(all_.items(), key=lambda kv: (kv[1]["folder"], kv[0])):
            # `·` marks a pack loaded from your private folder, so you can always see whether a pack in
            # play is the published one or yours (it is not in the repo, and not in git)
            print(f"{'*' if pid in chosen else ' '} {pid:22} {p['type']:9} {str(p['version'] or '—'):8} {p['label']}"
                  + ("  ·  private" if p.get("private") else ""))
        if deal:
            print(f"\n* = used by {deal.slug}" + ("" if chosen else " (none chosen yet)"))
        return
    if a.action == "show":
        if not a.ids:
            fail("bid packs show <id>")
        p = P.get(a.ids[0])
        print(f"{p['id']} — {p['label']} ({p['type']}, version {p['version'] or '—'})\n  folder: {p['path']}")
        meta = p["meta"]
        if p["type"] == "product":
            print(f"\ndomains ({len(meta.get('domains') or {})}):")
            for k, d in (meta.get("domains") or {}).items():
                print(f"  {k:16} {d.get('label', '')}")
            cat = meta.get("catalogue") or {}
            unsourced = [k for k, v in cat.items() if not P.sourced(v)]
            print(f"\ncatalogue: {len(cat)} module(s), {len(cat) - len(unsourced)} sourced, "
                  f"{len(unsourced)} with no evidence (a rating resting on those prints unverified)")
            for k, v in cat.items():
                print(f"  {k:20} {'✓ ' + str(v.get('evidence') or v.get('confirmed')) if P.sourced(v) else '· no source'}")
            if meta.get("scope_rules"):
                print("\nscope rules:")
                for r in meta["scope_rules"]:
                    print(f"  {r.get('id')}: {' '.join(str(r.get('text')).split())[:110]}…")
        for ck in (p["checks"].get("regulations") or []):
            print(f"  regulation: {ck['name']} (owner {ck.get('owner', '—')})")
        return
    if a.action == "check":
        d = None
        if a.deal or settings.load().get("current"):
            d = deal_arg(a)
        problems, unsourced = P.check(d)
        if problems:
            print("\n".join(f"✗ {x}" for x in problems))
            sys.exit(1)
        print("✓ every pack is valid")
        if unsourced:
            print(f"  {len(unsourced)} catalogue entry(s) have no source yet, so a rating resting on them "
                  "prints as unverified:")
            for x in unsourced:
                print(f"    · {x}")
            print("  fill `evidence:` or `confirmed:` in the pack, or leave them: unverified is honest")
        return
    if a.action in ("use", "add", "remove"):
        d_ = deal_arg(a)
        bid = d_.bid()
        chosen = list(bid.get("packs") or [])
        ids = a.ids or []
        if a.action == "use":
            for pid in ids:
                P.get(pid)
            chosen = ids
        elif a.action == "add":
            for pid in ids:
                P.get(pid)
                if pid not in chosen:
                    chosen.append(pid)
        else:
            chosen = [p for p in chosen if p not in ids]
        bid["packs"] = chosen
        d_.save_bid(bid)
        print(f"✓ packs: {', '.join(chosen) or 'none'}  (bid config check)")
        return
    if a.action == "suggest":
        deal = deal_arg(a)
        config, _ = layers.effective(deal)
        found = P.suggest(deal, config)
        if not found:
            print("No pack matched this RFP's wording — that is normal for a short or unusual pack; "
                  "the signals are only hints.\nChoose one yourself:\n"
                  + "\n".join(f"  {pid:20} {p['type']:9} {p['label']}" for pid, p in sorted(P.available().items()))
                  + "\nThen: bid packs use <id> [<id> ...]   (a product pack plus your region is the usual start)")
        for pid, why in found:
            print(f"  {pid:22} {P.available()[pid]['label']:32} matched: {why}")
        return
    fail(f"unknown packs action {a.action!r} (list, show, check, suggest, use, add, remove)")


def cmd_evidence(a):
    deal = deal_arg(a) if (a.deal or settings.load().get("current")) else None
    if a.action == "add" or a.action == "record":
        if not a.deal and deal is None:
            fail("no deal (bid new, or --deal)")
        key, _, text = (a.text or "").partition("=")
        if not key or not text:
            fail('bid evidence record KEY="what was confirmed"')
        evidence.record(deal, key.strip(), text.strip())
    if a.action in ("add", "record", "list"):
        conf = evidence.confirmations(deal)
        lib = evidence.library()
        print(f"library: {evidence.LIBRARY}" + ("" if lib else "  (empty)"))
        for eid, e in lib.items():
            print(f"  {eid:44} {e['topic'][:60]}")
        if deal is not None:
            print(f"\nconfirmations recorded for {deal.slug}:")
            for k, c in conf.items():
                print(f"  {k:24} {c['text'][:70]}  ({c['by']}, {c['date']})")
            if not conf:
                print("  none (bid evidence record KEY=\"…\")")
        return
    if a.action == "find":
        if not a.text:
            fail("bid evidence find \"a topic or a requirement's wording\"")
        hits = evidence.lookup(a.text, deal)
        if not hits:
            print("nothing found: a rating that relies on this should be unverified")
            return
        print(f"{hits['kind']} {hits['id']} (match {hits['score']})\n  {hits['source']}\n  {hits['snippet']}")
        return
    fail(f"unknown evidence action {a.action!r} (list, find, record)")


# ---------------------------------------------------------------- stages 3, 4, 5
def cmd_stage3(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    if a.action == "brief":
        print(stage3.brief(deal, config, a.domain))
    elif a.action == "save":
        if not a.file:
            fail("bid stage3 save FILE.json")
        try:
            data = json.loads(Path(a.file).read_text())
        except (OSError, json.JSONDecodeError) as e:
            fail(f"can't read {a.file}: {e}")
        out, problems = stage3.save(deal, data, config)
        if problems:
            print("✗ Stage 3 not saved:\n" + "\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        m = stage3.matrix(deal, config)
        print(f"✓ {out}: {m['rated']} of {m['requirements']} rated · {len(m['gaps'])} gaps · "
              f"{len(m['unverified'])} unverified · {m['domains_done']}/{m['domains_total']} domains done")
        if m["complete"]:
            print("  matrix complete: bid stage3 render")
    elif a.action == "render":
        path, problems = stage3.save_render(deal, config)
        if problems:
            print("✗ can't render Stage 3:\n" + "\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        print(f"✓ Stage 3 written: {path}")
    elif a.action == "matrix":
        m = stage3.matrix(deal, config)
        print(f"{m['rated']} of {m['requirements']} requirements rated ({m['domains_done']}/{m['domains_total']} domains)")
        for k, v in m["counts"].items():
            if v:
                print(f"  {k:18} {v}")
        print(f"covered {m['covered']} ({m['covered'] / max(m['rated'], 1):.0%}) · gaps {len(m['gaps'])} "
              f"(mandatory {len(m['mandatory_gaps'])}) · unverified {len(m['unverified'])}")
        if not m["complete"]:
            left = sorted({x["domain"] for x in m["rows"]}) if m["domains_done"] else []
            print(f"✗ the matrix is not complete: {m['requirements'] - m['rated']} requirement(s) unrated "
                  f"in {m['domains_total'] - m['domains_done']} domain(s)"
                  + (f" (rated so far: {', '.join(sorted({x['domain'] for x in m['rows']}))})" if left else ""))
            sys.exit(1)
    else:
        fail("bid stage3 brief [DOMAIN] | save FILE.json | matrix | render")


def cmd_stage4(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    if a.action == "brief":
        print(stage4.brief(deal, config))
    elif a.action == "save":
        if not a.file:
            fail("bid stage4 save FILE.json")
        try:
            data = json.loads(Path(a.file).read_text())
        except (OSError, json.JSONDecodeError) as e:
            fail(f"can't read {a.file}: {e}")
        out, problems = stage4.save(deal, data, config)
        if problems:
            print("✗ Stage 4 not saved:\n" + "\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        open_ = sum(1 for m in data.get("mitigations") or [] if not m.get("closes_it"))
        print(f"✓ Stage 4 saved: {out}\n  gaps mitigated {len(data.get('mitigations') or [])} · still open {open_}")
    elif a.action == "inputs":
        for field, v in stage4.inputs(deal, config).items():
            print(f"{field}: {len(v['have'])} recorded" + (f", missing {', '.join(v['missing'])}" if v["missing"] else ""))
    else:
        fail("bid stage4 brief | save FILE.json | inputs")


def cmd_stage5(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    if a.action == "brief":
        print(stage5.brief(deal, config))
    elif a.action == "save":
        if not a.file:
            fail("bid stage5 save FILE.json")
        try:
            data = json.loads(Path(a.file).read_text())
        except (OSError, json.JSONDecodeError) as e:
            fail(f"can't read {a.file}: {e}")
        out, problems = stage5.save(deal, data, config)
        if problems:
            print("✗ Stage 5 not saved:\n" + "\n".join(f"  - {p}" for p in problems))
            sys.exit(1)
        high = sum(1 for c in data.get("clauses") or [] if c.get("risk") in ("high", "unknown"))
        print(f"✓ Stage 5 saved: {out}\n  clauses needing Legal: {high}")
    else:
        fail("bid stage5 brief | save FILE.json")


def cmd_gate(a):
    deal = deal_arg(a)
    config, _ = layers.effective(deal)
    st = state.load(deal)
    s = st["stages"].get(a.stage)
    if a.stage not in (config.get("stages") or {}):
        fail(f"no stage {a.stage}")
    if a.stage == "stage3":
        # Stage 3 is gated on the matrix on disk, not on a rendered document: the ratings are the work,
        # and a stage that hasn't rendered yet is still reviewable domain by domain.
        m = stage3.matrix(deal, config)
        if not m["rated"]:
            fail("stage3 hasn't been run yet (bid stage3 brief)")
        why = []
        if not m["complete"]:
            why.append(f"the matrix isn't complete ({m['rated']} of {m['requirements']} rated)")
        if m["unverified"]:
            why.append(f"{len(m['unverified'])} rating(s) are unverified: source them, or record that you "
                       "accept them in --note")
        if why:
            fail("can't pass the Stage 3 gate: " + "; ".join(why))
    elif not s or not s.get("done"):
        fail(f"{a.stage} hasn't been run yet")
    if a.stage == "stage4":
        data = stage4.load(deal)
        open_ = [m["req"] for m in data.get("mitigations") or [] if not m.get("closes_it")]
        if open_ and not a.note:
            fail(f"{len(open_)} gap(s) stay open after mitigation ({', '.join(open_)}): say in --note that they are "
                 "known and accepted, e.g. --note \"Open gaps accepted by <AE>, <date>\"")
    if a.stage == "stage5":
        data = stage5.load(deal)
        highs = [c for c in data.get("clauses") or [] if c.get("risk") in ("high", "unknown")]
        if highs and not a.note:
            fail(f"{len(highs)} clause(s) are unacceptable as written: record Legal's position with --note")
    if a.stage == "stage1":
        why = []
        if not coverage.report(deal)["complete"]:
            why.append("extraction isn't complete (bid coverage)")
        sc = deal.path / "data" / "spotcheck.json"
        if not sc.exists() or json.loads(sc.read_text()).get("status") != "ok":
            why.append("the spot-check hasn't passed (bid spotcheck)")
        if why:
            fail("can't pass the Stage 1 gate: " + "; ".join(why))
    if a.stage == "stage2":
        if s.get("recommendation") == "Pending":
            fail("Stage 2 is Pending (criteria not scored): get the missing inputs and save it again")
        if not a.note:
            fail("say who agreed the decision, e.g. --note \"Agreed with Alex (AE), 24 Oct\"")
    if s is None:                              # a stage whose work is on disk but not yet rendered
        s = {"done": True, "version": 0, "saved": f"{dt.date.today():%Y-%m-%d}",
             **({"recommendation": None} if a.stage == "stage3" else {})}
        st["stages"][a.stage] = s
    s.update({"gate_passed": True, "gate_note": a.note or "", "gate_date": f"{dt.date.today():%Y-%m-%d}"})
    state.save(deal, st)
    print(f"✓ {config['stages'][a.stage]['name']}: gate passed"
          + (" (the matrix is rated but not rendered: bid stage3 render)" if a.stage == "stage3" and not s.get("version") else ""))


# ---------------------------------------------------------------- config
def cmd_config(a):
    if a.action == "show":
        return config_show(a)
    if a.action == "check":
        deal = deal_arg(a) if a.deal or settings.load().get("current") else None
        problems = layers.check(deal)
        if problems:
            print("\n".join(f"✗ {p}" for p in problems))
            sys.exit(1)
        print(f"✓ configuration is valid{' for ' + deal.slug if deal else ''}")
        return
    if a.action:
        fail(f"unknown config action {a.action!r} (show, check)")
    kv = {k: v for k, v in {"workspace": a.workspace, "customer_path": a.customer_path,
                            "subfolder": a.subfolder}.items() if v is not None}
    if kv.get("workspace"):
        p = Path(kv["workspace"]).expanduser()
        if not p.is_dir():
            fail(f"{p} is not a folder")
        kv["workspace"] = str(p.resolve())
    if kv:
        settings.save(**kv)
    for k in settings.DEFAULTS:
        v = settings.get(k)
        print(f"{k}: {v if v else 'not set'}")
    print(f"profile: {PROFILE}" + ("" if PROFILE.is_dir() and any(PROFILE.glob('*.yaml')) else "  (empty: shipped defaults)"))


def config_show(a):
    deal = deal_arg(a) if a.deal or settings.load().get("current") else None
    config, prov = layers.effective(deal)
    want = a.id or ""
    rows = [(p, l) for p, l in prov.items() if p == want or p.startswith(want + ".") or not want]
    if not rows:
        fail(f"no setting `{want}`")
    for path, label in rows:
        v = config
        for part in path.split("."):
            v = v[part]
        print(f"{path} = {v}    [{label}]")


# ---------------------------------------------------------------- install checks
def cmd_doctor(a):
    ok = True

    def line(good, msg, fix=""):
        nonlocal ok
        ok &= good
        print(f"  {'✓' if good else '✗'} {msg}" + (f"  ({fix})" if fix and not good else ""))

    # 3.9 is the real floor: no PEP 604 unions or 3.10-only syntax anywhere in the code, and the full
    # test suite passes on 3.9.6. Claiming 3.10 was wrong and put first-time users off for no reason.
    line(sys.version_info >= (3, 9), f"Python {sys.version.split()[0]}", "needs 3.9+")
    try:
        import yaml
        line(True, f"PyYAML {yaml.__version__}")
    except ImportError:
        line(False, "PyYAML", "run: bash hosts/install-all.sh")
    w = ws.workspace()
    line(w is None or w.is_dir(), f"workspace: {w or 'not set (deals go to BidForge deals/)'}", "bid config --workspace PATH")

    # Hosts: report the ones installed and the ones still missing, rather than only the two we used
    # to support. A host whose settings folder doesn't exist isn't a failure — you just don't use it.
    env = os.environ
    home = Path.home()
    hosts = [
        ("Claude Code", Path(env.get("CLAUDE_CONFIG_DIR") or home / ".claude"),
         ["skills/bid/SKILL.md"], True),
        ("OpenCode", Path(env.get("OPENCODE_CONFIG_DIR") or home / ".config/opencode"),
         ["commands/bid.md"], True),
        ("Hermes", Path(env.get("HERMES_HOME") or home / ".hermes"),
         ["skills/bid/SKILL.md"], True),
        ("Goose", Path(env.get("GOOSE_CONFIG_DIR") or home / ".config/goose"),
         ["recipes/bid.yaml"], True),
        ("omp", Path(env.get("OMP_AGENT_DIR") or home / ".omp/agent"),
         ["commands/bid.md"], True),
        ("Open Worker", Path(env.get("COWORKER_HOME") or home / ".config/coworker"),
         ["skills/bid/SKILL.md"], True),
    ]
    installed, absent = [], []
    for name, base, rels, _ in hosts:
        present = base.is_dir()
        ready = present and all((base / r).exists() for r in rels)
        if ready:
            installed.append(name)
        elif present:
            absent.append(name)          # the tool is here but BidForge isn't registered in it
    if installed:
        line(True, "hosts with /bid: " + ", ".join(installed))
    if absent:
        line(False, "installed but missing /bid: " + ", ".join(absent), "bash hosts/install-all.sh")
    if not installed and not absent:
        line(False, "no supported AI host found", "install one (Claude Code, OpenCode, Hermes, Goose, omp or Open Worker)")
    plugins = P.available()
    private = [p for p in plugins.values() if p.get("private")]
    line(True, f"packs: {len(plugins)} installed" + (f", {len(private)} private" if private else ""))
    problems = layers.check()
    line(not problems, "configuration (defaults + personal profile)", "bid config check")
    sys.exit(0 if ok else 1)


def cmd_selftest(a):
    codes = [subprocess.call([sys.executable, str(ROOT / "tests" / t)])
             for t in ("selftest.py", "e2e.py", "e2e_stages.py")]
    sys.exit(max(codes))


# ---------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(prog="bid", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new"); s.set_defaults(fn=cmd_new)
    s.add_argument("customer"); s.add_argument("--rfp", required=True)
    s.add_argument("--files", nargs="*"); s.add_argument("--folder"); s.add_argument("--parent")
    s.add_argument("--pick", type=int)

    s = sub.add_parser("where"); s.set_defaults(fn=cmd_where)
    s.add_argument("customer"); s.add_argument("--create", action="store_true"); s.add_argument("--parent")
    s.add_argument("--pick", type=int); s.add_argument("--folder")

    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("use"); s.set_defaults(fn=cmd_use); s.add_argument("name")

    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status); s.add_argument("--deal")

    s = sub.add_parser("pack"); s.set_defaults(fn=cmd_pack)
    s.add_argument("action", choices=["add"]); s.add_argument("files", nargs="+"); s.add_argument("--deal")

    s = sub.add_parser("team"); s.set_defaults(fn=cmd_team)
    s.add_argument("assign", nargs="*", metavar="role=person"); s.add_argument("--deal")

    s = sub.add_parser("config"); s.set_defaults(fn=cmd_config)
    s.add_argument("action", nargs="?"); s.add_argument("id", nargs="?")
    s.add_argument("--workspace"); s.add_argument("--customer-path"); s.add_argument("--subfolder")
    s.add_argument("--deal")

    s = sub.add_parser("intake"); s.set_defaults(fn=cmd_intake); s.add_argument("--force", action="store_true")
    s.add_argument("--remark", action="store_true")
    s.add_argument("--deal")
    s = sub.add_parser("extract"); s.set_defaults(fn=cmd_extract)
    s.add_argument("action", choices=["next", "show", "save"]); s.add_argument("chunk", nargs="?")
    s.add_argument("file", nargs="?"); s.add_argument("--deal")
    s = sub.add_parser("coverage"); s.set_defaults(fn=cmd_coverage); s.add_argument("--deal")
    s = sub.add_parser("spotcheck"); s.set_defaults(fn=cmd_spotcheck); s.add_argument("--deal")
    s.add_argument("--ok", action="store_true"); s.add_argument("--issues")
    s = sub.add_parser("stage1"); s.set_defaults(fn=cmd_stage1)
    s.add_argument("action", choices=["brief", "save"]); s.add_argument("file", nargs="?"); s.add_argument("--deal")
    s = sub.add_parser("capture"); s.set_defaults(fn=cmd_capture)
    s.add_argument("assign", nargs="*", metavar="KEY=answer"); s.add_argument("--deal")
    s = sub.add_parser("stage2"); s.set_defaults(fn=cmd_stage2)
    s.add_argument("action", choices=["brief", "save"]); s.add_argument("file", nargs="?"); s.add_argument("--deal")
    s = sub.add_parser("packs"); s.set_defaults(fn=cmd_packs)
    s.add_argument("action", nargs="?"); s.add_argument("ids", nargs="*")
    s.add_argument("--deal")
    s = sub.add_parser("evidence"); s.set_defaults(fn=cmd_evidence)
    s.add_argument("action", nargs="?", choices=[None, "list", "find", "record", "add"])
    s.add_argument("text", nargs="?"); s.add_argument("--deal")
    s = sub.add_parser("stage3"); s.set_defaults(fn=cmd_stage3)
    s.add_argument("action", choices=["brief", "save", "matrix", "render"])
    s.add_argument("file", nargs="?"); s.add_argument("--domain", dest="domain"); s.add_argument("--deal")
    s = sub.add_parser("stage4"); s.set_defaults(fn=cmd_stage4)
    s.add_argument("action", choices=["brief", "save", "inputs"])
    s.add_argument("file", nargs="?"); s.add_argument("--deal")
    s = sub.add_parser("stage5"); s.set_defaults(fn=cmd_stage5)
    s.add_argument("action", choices=["brief", "save"])
    s.add_argument("file", nargs="?"); s.add_argument("--deal")
    s = sub.add_parser("gate"); s.set_defaults(fn=cmd_gate)
    s.add_argument("action", choices=["pass"]); s.add_argument("stage"); s.add_argument("--note"); s.add_argument("--deal")

    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)

    a = p.parse_args()
    try:
        a.fn(a)
    except layers.ConfigError as e:
        fail(e)


if __name__ == "__main__":
    main()
