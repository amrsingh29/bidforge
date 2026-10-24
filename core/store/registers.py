"""The Unknown (U-xx) and Confirm (C-xx) registers, carried across stages. Items are never deleted.

    add(deal, kind, text, stage, source=None, role=None, question=None) -> id
    items(deal) -> [item]
    replace_stage(deal, stage, new_items) -> ids   a stage re-run replaces its own open items, keeping IDs
"""
from core.store import files


def _path(deal):
    return deal.path / "data" / "registers.json"


def items(deal):
    return files.read(_path(deal), {"items": []})["items"]


def _save(deal, its):
    files.write(_path(deal), {"items": its})


def replace_stage(deal, stage, new):
    """new: [{"kind": "U"|"C", "text", "source", "role", "question"}]. Items this stage raised before and
    raises again keep their IDs; ones it no longer raises are closed as "superseded", never deleted."""
    its = items(deal)
    mine = [i for i in its if i["stage"] == stage and i["status"] == "open"]
    ids = []
    for n in new:
        same = next((i for i in mine if i["kind"] == n["kind"] and i["text"].strip().lower() == n["text"].strip().lower()), None)
        if same:
            mine.remove(same)
            same.update({k: v for k, v in n.items() if k in ("source", "role", "question") and v})
            ids.append(same["id"])
            continue
        k = n["kind"]
        num = max([int(i["id"][2:]) for i in its if i["kind"] == k] + [0]) + 1
        item = {"id": f"{k}-{num:02d}", "kind": k, "text": n["text"].strip(), "stage": stage, "status": "open",
                "source": n.get("source"), "role": n.get("role"), "question": n.get("question")}
        its.append(item)
        ids.append(item["id"])
    for old in mine:
        old["status"] = "superseded"
    _save(deal, its)
    return ids
