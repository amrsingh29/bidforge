"""BidForge self-test: runs the CLI in a throwaway home and workspace, never touching your own.

    python tests/selftest.py      (or `bid selftest`)
"""
import os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BID = [sys.executable, str(ROOT / "cli" / "bid.py")]
failures = []


def run(*args, env, ok=True):
    r = subprocess.run(BID + list(args), env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    if (r.returncode == 0) != ok:
        failures.append(f"bid {' '.join(args)} exited {r.returncode}:\n{out}")
    return out


def expect(cond, what):
    print(f"  {'✓' if cond else '✗'} {what}")
    if not cond:
        failures.append(what)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    home, wsp = tmp / "home", tmp / "workspace"
    cust = wsp / "Singapore" / "Acme Bank"
    (cust / "RFP").mkdir(parents=True)
    (cust / "RFP" / "main-rfp.docx").write_text("x")
    (cust / "RFP" / "annex-a.xlsx").write_text("x")
    (cust / "RFP" / "~$main-rfp.docx").write_text("lock")      # Office lock file: never part of the pack
    (cust / "notes.md").write_text("the user's own file")
    env = {**os.environ, "BIDFORGE_HOME": str(home)}

    print("settings and deals")
    run("config", "--workspace", str(wsp), env=env)
    out = run("new", "acme bank", "--rfp", "ITSM RFP 2026", "--files", str(cust / "RFP"), env=env)
    deal = cust / "bidforge" / "itsm-rfp-2026"
    expect((deal / "bid.yaml").exists(), "deal created inside the customer's own folder (found by name at depth 2)")
    expect("2 file(s)" in out, "pack holds the folder's files, without the Office lock file")
    expect((cust / "notes.md").read_text() == "the user's own file", "the user's own files are untouched")
    out = run("status", env=env)
    expect("Inventory & understanding" in out and "not started" in out, "status lists the stages")
    expect("not built yet" in out, "status says honestly that stages aren't built yet")
    expect("not extracted yet" in out, "status: no dates before Stage 1")

    print("team")
    run("team", "presales=Alex", "sales=Sam,Jordan", env=env)
    out = run("status", env=env)
    expect("Alex" in out and "Sam, Jordan" in out, "people named per deal, several per role")
    run("team", "wizard=Merlin", env=env, ok=False)
    expect(True, "unknown role refused")

    print("configuration layers")
    (home / "profile").mkdir(parents=True)
    (home / "profile" / "my-way.yaml").write_text(
        "stages:\n"
        "  stage4: {gate: hard}\n"
        "  stage7: {enabled: false}\n"
        "  partner_check: {name: Partner assessment, gate: soft, after: stage2}\n"
        "roles:\n  marketing: {enabled: false}\n")
    out = run("config", "show", "stages.stage4.gate", env=env)
    expect("hard" in out and "personal (my-way.yaml)" in out, "personal layer wins, with provenance")
    out = run("status", env=env)
    lines = [l for l in out.splitlines() if l.strip()[:2] in {f"{i}." for i in range(1, 10)}]
    names = [l.split(".", 1)[1].strip() for l in lines]
    expect(names[2].startswith("Partner assessment"), "custom stage placed right after stage 2")
    expect(not any(n.startswith("Win strategy") for n in names), "stage turned off")
    bid = (deal / "bid.yaml").read_text()
    (deal / "bid.yaml").write_text(bid.replace("overrides: {}", "overrides:\n  stages:\n    stage4: {gate: soft}"))
    out = run("config", "show", "stages.stage4.gate", env=env)
    expect("soft" in out and "deal (bid.yaml)" in out, "deal layer wins over personal")
    out = run("config", "check", env=env)
    expect("valid" in out, "valid configuration passes check")

    print("config check catches mistakes")
    (home / "profile" / "typo.yaml").write_text(
        "stages:\n  stage2: {gaet: hard}\n  bad: {name: Bad, gate: maybe, after: nowhere}\n")
    out = run("config", "check", env=env, ok=False)
    expect("unknown ID `stages.stage2.gaet`" in out, "typo in a key")
    expect("must be hard or soft" in out, "invalid gate")
    expect("no stage `nowhere`" in out, "custom stage after a stage that doesn't exist")
    (home / "profile" / "typo.yaml").unlink()

    print("several deals")
    run("new", "Other Co", "--rfp", "AIOps RFI", "--parent", "Malaysia", env=env)
    expect((wsp / "Malaysia" / "Other Co" / "bidforge" / "aiops-rfi" / "bid.yaml").exists(), "new customer folder created on request")
    out = run("list", env=env)
    expect("acme-bank-itsm-rfp-2026" in out and "* other-co-aiops-rfi" in out, "both deals listed, newest current")
    run("use", "acme", env=env)
    out = run("status", env=env)
    expect("Acme" in out or "acme" in out, "switch deals by partial name")

print()
if failures:
    print(f"✗ selftest: {len(failures)} failure(s)")
    for f in failures:
        print("  - " + f.replace("\n", "\n    "))
    sys.exit(1)
print("✓ selftest passed")
