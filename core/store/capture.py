"""Capture inputs: what the pack can't tell us (relationship, incumbent, competitors…), from the user.

    load(deal) -> {key: {"value", "by", "date"}}
    set_(deal, key, value, by="user") · missing(deal, config) -> [key]
"""
import datetime as dt

from core.store import files


def _path(deal):
    return deal.path / "data" / "capture.json"


def load(deal):
    return files.read(_path(deal), {})


def set_(deal, key, value, by="user"):
    data = load(deal)
    if value.strip():
        data[key] = {"value": value.strip(), "by": by, "date": f"{dt.date.today():%Y-%m-%d}"}
    else:
        data.pop(key, None)
    files.write(_path(deal), data)
    return data


def missing(deal, config):
    asked = (config.get("qualification") or {}).get("capture") or {}
    have = load(deal)
    return [k for k in asked if k not in have]
