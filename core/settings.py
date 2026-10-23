"""Machine-specific settings that never go to git: ~/.bidforge/settings.json.

    workspace      root folder holding customer folders (none -> BidForge's own deals/)
    customer_path  "auto" (find the customer folder by name at any depth) or a pattern like "{country}/{customer}"
    subfolder      the only folder BidForge writes inside a customer folder
    customers      remembered customer folders (by normalised name)
    deals          known deals (slug -> deal folder); `current` is the one /bid works on
"""
import json

from core.paths import HOME, SETTINGS

DEFAULTS = {"workspace": None, "customer_path": "auto", "subfolder": "bidforge"}


def load():
    return json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}


def save(**kv):
    cfg = load()
    cfg.update(kv)
    HOME.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(cfg, indent=2) + "\n")
    return cfg


def get(key):
    return load().get(key, DEFAULTS.get(key))
