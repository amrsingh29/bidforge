"""Where a customer's folder is, from the user's own settings (same behaviour as StoryForge).

    resolve("BW Digital")      -> Path of the customer folder (or raises Ambiguous / NotFound)
    create("BW Digital", "Singapore") -> a new customer folder under the workspace
    remember(customer, path)   -> pin a folder whose name doesn't match the customer name

Customer folders are found by name at any depth under `workspace` (customer_path "auto"), or by a
pattern such as "{customer}" or "{country}/{customer}". Names match ignoring case, spaces and
punctuation. BidForge only ever writes inside the customer folder's `subfolder`.
"""
import os, re
from pathlib import Path

from core import settings

MAX_DEPTH = 4


class NotFound(LookupError):
    pass


class Ambiguous(LookupError):
    def __init__(self, customer, candidates):
        super().__init__(f"{customer} matches {len(candidates)} folders")
        self.candidates = candidates


def norm(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:60] or "deal"


def workspace():
    ws = settings.get("workspace")
    return Path(ws).expanduser() if ws else None


def _walk(root: Path, sub: str):
    """Folders under root up to MAX_DEPTH, skipping hidden/underscore folders and BidForge's own."""
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            kids = sorted((e for e in os.scandir(d) if e.is_dir(follow_symlinks=False)), key=lambda e: e.name.lower())
        except OSError:
            continue
        for e in kids:
            if e.name.startswith((".", "_")) or e.name == sub:
                continue
            yield Path(e.path), depth + 1
            if depth + 1 < MAX_DEPTH:
                stack.append((Path(e.path), depth + 1))


def candidates(customer):
    ws = workspace()
    if not ws:
        return []
    if not ws.is_dir():
        raise NotFound(f"workspace {ws} does not exist (bid config --workspace PATH)")
    want, pat = norm(customer), settings.get("customer_path")
    if pat and pat != "auto":
        glob = re.sub(r"\{(?!customer\})[^}]+\}", "*", pat).replace("{customer}", "*")
        hidden = lambda p: any(part.startswith((".", "_")) for part in p.relative_to(ws).parts)
        return sorted(p for p in ws.glob(glob) if p.is_dir() and norm(p.name) == want and not hidden(p))
    found = sorted(_walk(ws, settings.get("subfolder")), key=lambda x: (x[1], str(x[0])))
    return [p for p, _ in found if norm(p.name) == want]


def resolve(customer, pick=None):
    """The customer's folder. A remembered choice wins; several matches raise Ambiguous unless `pick`
    (1-based) chooses one, which is then remembered."""
    ws = workspace()
    if not ws:
        raise NotFound("no workspace set: deals are saved in BidForge's deals/ (bid config --workspace PATH)")
    remembered = (settings.load().get("customers") or {}).get(norm(customer))
    if remembered and pick is None and Path(remembered).is_dir():
        return Path(remembered)
    found = candidates(customer)
    if not found:
        raise NotFound(f"no folder named \"{customer}\" under {ws}")
    if len(found) > 1 and pick is None:
        raise Ambiguous(customer, found)
    chosen = found[(pick or 1) - 1]
    if len(found) > 1:
        remember(customer, chosen)
    return chosen


def remember(customer, path):
    path = Path(path).expanduser().resolve()
    if not path.is_dir():
        raise NotFound(f"{path} is not a folder")
    known = settings.load().get("customers") or {}
    known[norm(customer)] = str(path)
    settings.save(customers=known)
    return path


def create(customer, parent=""):
    """Create a customer folder under workspace/<parent> (parent like "Singapore", or "" for flat)."""
    ws = workspace()
    if not ws:
        raise NotFound("no workspace set (bid config --workspace PATH)")
    pat = settings.get("customer_path")
    if pat and pat != "auto" and not parent and re.search(r"\{(?!customer\})[^}]+\}", pat):
        raise NotFound(f"customer_path is {pat}: say which folder to create it in, e.g. --parent Singapore")
    d = ws / parent / customer
    d.mkdir(parents=True, exist_ok=True)
    return remember(customer, d)
