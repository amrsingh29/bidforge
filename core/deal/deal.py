"""One RFP = one deal folder, inside the customer's folder (or BidForge's deals/ without a workspace).

    <customer>/bidforge/<rfp>/
        bid.yaml    customer, rfp, team, packs, overrides (this RFP only)
        pack.yaml   the files that make up the RFP pack (paths, never copies)
        data/       machine-readable state: state.json, requirements, registers
        stages/     stage-N.md, earlier versions kept
        output/     workbook, one-pager, clarifications

    Deal.create(customer_folder, customer, rfp, files) · Deal.find(name) · Deal.current()
"""
import datetime as dt
from pathlib import Path

import yaml

from core import settings
from core.deal import workspace as ws
from core.paths import LOCAL_DEALS

PACK_SKIP = (".", "~$")                  # hidden files and Office lock files are never part of the pack

BID_TEMPLATE = """\
# BidForge deal. BidForge rewrites this file when you use `bid team` or `bid packs`: values are kept,
# comments are not. Edit freely; `bid config check` tells you if something is wrong.
{body}"""


class DealError(LookupError):
    pass


class Deal:
    def __init__(self, path: Path):
        self.path = Path(path)
        if not (self.path / "bid.yaml").exists():
            raise DealError(f"{self.path} is not a BidForge deal (no bid.yaml)")

    @property
    def slug(self):
        return f"{ws.slug(self.bid()['customer'])}-{self.path.name}"

    def bid(self):
        return yaml.safe_load((self.path / "bid.yaml").read_text(encoding="utf-8")) or {}

    def save_bid(self, data):
        body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
        (self.path / "bid.yaml").write_text(BID_TEMPLATE.format(body=body), encoding="utf-8")

    def pack(self):
        p = self.path / "pack.yaml"
        return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("files", []) if p.exists() else []

    def add_files(self, paths):
        files = self.pack()
        known = {f["path"] for f in files}
        added = []
        for p in expand(paths):
            if str(p) not in known:
                files.append({"path": str(p), "added": f"{dt.date.today():%Y-%m-%d}"})
                known.add(str(p)); added.append(p)
        (self.path / "pack.yaml").write_text(
            "# The RFP pack: paths to the buyer's files, never copies. Add more with `bid pack add`.\n"
            + yaml.safe_dump({"files": files}, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return added

    # ------------------------------------------------------------ registry
    @classmethod
    def create(cls, base: Path, customer, rfp, files=()):
        d = base / ws.slug(rfp)
        if (d / "bid.yaml").exists():
            raise DealError(f"a deal already exists at {d} (bid use {ws.slug(customer)}-{d.name})")
        for sub in ("data", "stages", "output"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        (d / "bid.yaml").touch()
        deal = cls(d)
        deal.save_bid({"customer": customer, "rfp": rfp, "created": f"{dt.date.today():%Y-%m-%d}",
                       "team": {}, "packs": [], "overrides": {}})
        deal.add_files(files)
        register(deal, current=True)
        return deal

    @classmethod
    def find(cls, name):
        known = settings.load().get("deals") or {}
        if name in known:
            return cls(Path(known[name]))
        hits = [s for s in known if ws.norm(name) in ws.norm(s)]
        if len(hits) == 1:
            return cls(Path(known[hits[0]]))
        if hits:
            raise DealError(f"\"{name}\" matches several deals: {', '.join(hits)}")
        raise DealError(f"no deal \"{name}\" (bid list)")

    @classmethod
    def current(cls):
        cur = settings.load().get("current")
        if not cur:
            raise DealError("no current deal: start one with `bid new` or pick one with `bid use`")
        return cls.find(cur)


def deal_base(customer, folder=None, pick=None, parent=None):
    """Where a customer's deals go: <customer folder>/<subfolder>, or deals/<customer> without a workspace."""
    if folder:
        cust = ws.remember(customer, folder)
    elif ws.workspace() is None:
        return LOCAL_DEALS / ws.slug(customer)
    else:
        try:
            cust = ws.resolve(customer, pick)
        except ws.NotFound:
            if parent is None:
                raise
            cust = ws.create(customer, parent)
    return cust / settings.get("subfolder")


def register(deal, current=False):
    known = settings.load().get("deals") or {}
    known[deal.slug] = str(deal.path)
    kv = {"deals": known}
    if current:
        kv["current"] = deal.slug
    settings.save(**kv)


def expand(paths):
    """Files from paths; a folder adds every file inside it (any depth), skipping hidden and lock files."""
    out = []
    for p in paths:
        p = Path(p).expanduser().resolve()
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.is_file() and not any(
                part.startswith(PACK_SKIP) for part in f.relative_to(p).parts))
        elif p.is_file():
            out.append(p)
        else:
            raise DealError(f"{p} does not exist")
    return out
