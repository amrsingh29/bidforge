"""A deal's progress, on disk (data/state.json), so any session in any host picks up where the last stopped.

    load(deal) / save(deal, state)
    stage_status(state, sid)   "not started" | "done" | "done, gate open"
    next_step(deal, config)    what `/bid` runs next, or the gate it is waiting on
"""
import json

from core.config.layers import ordered_stages


def load(deal):
    p = deal.path / "data" / "state.json"
    return json.loads(p.read_text()) if p.exists() else {"stages": {}}


def save(deal, state):
    (deal.path / "data" / "state.json").write_text(json.dumps(state, indent=2) + "\n")


def stage_status(state, sid):
    s = state.get("stages", {}).get(sid)
    if not s or not s.get("done"):
        return "not started"
    return "done" if s.get("gate_passed") else "done, gate open"


def next_step(deal, config):
    """(kind, stage id, stage) with kind "run" | "gate" | "finished"."""
    state = load(deal)
    for sid, stage in ordered_stages(config):
        st = stage_status(state, sid)
        if st == "not started":
            return "run", sid, stage
        if st == "done, gate open" and stage.get("gate") == "hard":
            return "gate", sid, stage
    return "finished", None, None


def registers(deal):
    """Open Unknown (U-xx) and Confirm (C-xx) items. Stages fill data/registers.json from Phase 2."""
    p = deal.path / "data" / "registers.json"
    items = json.loads(p.read_text()).get("items", []) if p.exists() else []
    open_ = [i for i in items if i.get("status") != "closed"]
    return {"U": sum(i["id"].startswith("U-") for i in open_), "C": sum(i["id"].startswith("C-") for i in open_)}


def deadlines(deal):
    """Key dates from Stage 1 (data/dates.json); empty until Stage 1 has run."""
    p = deal.path / "data" / "dates.json"
    return json.loads(p.read_text()).get("milestones", []) if p.exists() else []
