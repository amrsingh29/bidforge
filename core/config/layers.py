"""Configuration layers: shipped default -> personal profile -> deal. Later layers win.

    effective(deal=None) -> (config, provenance)   provenance: "stages.stage2.gate" -> "personal (stages.yaml)"
    ordered_stages(config) -> [(id, stage)]       enabled stages in run order (custom stages placed by `after`)
    check(deal=None) -> [problem, ...]            empty when the configuration is valid

The four actions, on any ID such as `stages.stage2.gate`:
    change    set the key to a new value
    add       a new key inside a collection (stages, roles, modes), e.g. a custom stage with `after:`
    turn off  `enabled: false`
    replace   `{replace: <value>}` swaps the whole value instead of merging into it

Lists are replaced, not merged. Personal files are any *.yaml in ~/.bidforge/profile/; a deal's
overrides are the `overrides:` key of its bid.yaml.
"""
from pathlib import Path

import yaml

from core.paths import DEFAULTS, PROFILE

GATES = {"hard", "soft"}


class ConfigError(ValueError):
    pass


def read_yaml(path: Path):
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: not valid YAML ({e})") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected keys at the top level")
    return data


def meta():
    return read_yaml(DEFAULTS / "meta.yaml")


def layers(deal=None):
    """[(layer label, data)] in merge order."""
    out = [(f"default ({p.name})", read_yaml(p)) for p in sorted(DEFAULTS.glob("*.yaml")) if p.name != "meta.yaml"]
    if PROFILE.is_dir():
        out += [(f"personal ({p.name})", read_yaml(p)) for p in sorted(PROFILE.glob("*.yaml"))]
    if deal is not None:
        out.append(("deal (bid.yaml)", deal.bid().get("overrides") or {}))
    return out


def _merge(base, over, label, prov, path=""):
    for k, v in over.items():
        p = f"{path}.{k}" if path else str(k)
        if isinstance(v, dict) and set(v) == {"replace"}:
            base[k] = v["replace"]
            _mark(base[k], label, prov, p)
        elif isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v, label, prov, p)
        else:
            base[k] = v
            _mark(v, label, prov, p)


def _mark(v, label, prov, path):
    for stale in [x for x in prov if x == path or x.startswith(path + ".")]:
        del prov[stale]
    if isinstance(v, dict) and v:
        for k, sub in v.items():
            _mark(sub, label, prov, f"{path}.{k}")
    else:
        prov[path] = label


def effective(deal=None):
    config, prov = {}, {}
    for label, data in layers(deal):
        _merge(config, data, label, prov)
    return config, prov


def ordered_stages(config):
    stages = {k: v for k, v in (config.get("stages") or {}).items() if isinstance(v, dict) and v.get("enabled", True)}
    placed = sorted((k for k, v in stages.items() if "after" not in v), key=lambda k: stages[k].get("order", 99))
    pending = [k for k in stages if k not in placed]
    while pending:                                    # custom stages go right after the stage they name
        progressed = False
        for k in list(pending):
            anchor = stages[k]["after"]
            if anchor in placed:
                placed.insert(placed.index(anchor) + 1, k)
                pending.remove(k)
                progressed = True
        if not progressed:                            # anchor missing or disabled: check() reports it
            placed += pending
            break
    return [(k, stages[k]) for k in placed]


def _unknown(defaults, over, collections, allowed, path=""):
    for k, v in over.items():
        p = f"{path}.{k}" if path else str(k)
        if not isinstance(defaults, dict) or k not in defaults:
            if path not in collections and k not in allowed:
                yield p
            continue
        if isinstance(v, dict) and set(v) != {"replace"}:
            yield from _unknown(defaults[k], v, collections, allowed, p)


def check(deal=None):
    problems = []
    try:
        all_layers = layers(deal)
        m = meta()
    except ConfigError as e:
        return [str(e)]
    collections, allowed = set(m.get("collections", [])), set(m.get("always_allowed", []))
    defaults = {}
    for label, data in all_layers:
        if label.startswith("default"):
            _merge(defaults, data, label, {})
        else:
            problems += [f"{label}: unknown ID `{p}` (typo? new keys are allowed only in {', '.join(sorted(collections))})"
                         for p in _unknown(defaults, data, collections, allowed)]
    config, _ = effective(deal)
    stages = config.get("stages") or {}
    for sid, s in stages.items():
        if not isinstance(s, dict):
            problems.append(f"stages.{sid}: expected a stage (name, gate, ...)")
            continue
        if not s.get("name"):
            problems.append(f"stages.{sid}: has no name")
        if s.get("gate") not in GATES:
            problems.append(f"stages.{sid}.gate: must be hard or soft, not {s.get('gate')!r}")
        if "after" in s and s["after"] not in stages:
            problems.append(f"stages.{sid}.after: no stage `{s['after']}`")
        elif "after" in s and not stages[s["after"]].get("enabled", True):
            problems.append(f"stages.{sid}.after: `{s['after']}` is turned off")
    q = config.get("qualification") or {}
    crit = {k: v for k, v in (q.get("scorecard") or {}).items() if isinstance(v, dict) and v.get("enabled", True)}
    total = sum(v.get("weight", 0) for v in crit.values())
    if crit and total != 100:
        problems.append(f"qualification.scorecard: weights add up to {total}, not 100 "
                        f"({', '.join(f'{k} {v.get("weight", 0)}' for k, v in crit.items())})")
    th = q.get("thresholds") or {}
    if th and not (0 <= th.get("conditions", 0) <= th.get("bid", 0) <= 100):
        problems.append("qualification.thresholds: need 0 ≤ conditions ≤ bid ≤ 100")
    for mid, m in (config.get("modes") or {}).items():
        for sid in (m or {}).get("stages", []):
            if sid not in stages:
                problems.append(f"modes.{mid}.stages: no stage `{sid}`")
    if deal is not None:
        roles = config.get("roles") or {}
        for role in (deal.bid().get("team") or {}):
            if role not in roles:
                problems.append(f"bid.yaml team: `{role}` is not a role (bid config show roles)")
            elif not roles[role].get("enabled", True):
                problems.append(f"bid.yaml team: `{role}` is turned off in your configuration")
    return problems
