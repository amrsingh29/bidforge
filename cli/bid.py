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
  bid doctor                         check the install
  bid selftest                       run the self-test in a throwaway home and workspace

Settings and your personal profile live in ~/.bidforge (BIDFORGE_HOME overrides).
"""
import argparse, datetime as dt, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import settings                                               # noqa: E402
from core.config import layers                                          # noqa: E402
from core.deal import workspace as ws                                   # noqa: E402
from core.deal.deal import Deal, DealError, deal_base                   # noqa: E402
from core.paths import PROFILE                                          # noqa: E402
from core.store import state                                            # noqa: E402

# Stages whose engine exists. Grows phase by phase (PLAN.md); the skill never pretends otherwise.
BUILT = set()


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
    if kind == "finished":
        print("Next:   all stages done (bid export)")
    elif kind == "gate":
        print(f"Next:   waiting for you at the {s['name']} gate: {s.get('gate_check', '')}")
    else:
        print(f"Next:   {s['name']}" + ("" if sid in BUILT else " — not built yet (PLAN.md phases)"))
    problems = layers.check(deal)
    if problems:
        print(f"⚠ configuration: {len(problems)} problem(s) (bid config check)")


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

    line(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}", "needs 3.10+")
    try:
        import yaml
        line(True, f"PyYAML {yaml.__version__}")
    except ImportError:
        line(False, "PyYAML", "re-run core/hosts/install.sh")
    w = ws.workspace()
    line(w is None or w.is_dir(), f"workspace: {w or 'not set (deals go to BidForge deals/)'}", "bid config --workspace PATH")
    claude = Path.home() / ".claude/skills/bid"
    line(claude.exists(), "Claude Code skill /bid", "re-run core/hosts/install.sh")
    oc = Path(os.environ.get("OPENCODE_CONFIG_DIR", Path.home() / ".config/opencode")) / "commands/bid.md"
    line(oc.exists(), "OpenCode command /bid", "re-run core/hosts/install.sh")
    problems = layers.check()
    line(not problems, "configuration (defaults + personal profile)", "bid config check")
    sys.exit(0 if ok else 1)


def cmd_selftest(a):
    sys.exit(subprocess.call([sys.executable, str(ROOT / "tests" / "selftest.py")]))


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

    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)

    a = p.parse_args()
    try:
        a.fn(a)
    except layers.ConfigError as e:
        fail(e)


if __name__ == "__main__":
    main()
