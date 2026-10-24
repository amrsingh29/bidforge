"""The code pass: mark every block that may hold a requirement, and why.

    mark(blocks, config)    sets block["cand"] to a reason ("wording", "list item", "table row",
                            "matrix row", "sheet row") or None, and fills matrix fields

The model pass must then account for every candidate: each one is cited by a requirement or
dismissed with a reason. That is what makes the coverage report meaningful.
"""
import re

ID_LIKE = re.compile(r"^[\w.#/-]{1,12}$")
BULLET = re.compile(r"^\s*[■□▪▫●○•◦▸►✓✔➢–-]\s+")
NUMBER = re.compile(r"^[-+]?[\d,]*\.?\d+%?$")


def wording(config):
    words = config["requirements"]["candidate_words"]
    return re.compile(r"\b(?:" + "|".join(words) + r")\b", re.I)


def matrix_columns(header, config):
    """{requirement: i, reference: i, section: i} when a sheet header looks like a compliance matrix."""
    if not header:
        return None
    names = [(h or "").lower().replace("\n", " ") for h in header]
    want = config["requirements"]["matrix_headers"]
    found = {}
    for role, words in want.items():
        for i, n in enumerate(names):
            if any(w in n for w in words) and i not in found.values():
                found[role] = i
                break
    return found if "requirement" in found and ("reference" in found or "section" in found) else None


def mark(blocks, config):
    modal = wording(config)
    intro = {}                                     # (doc, section) -> the paragraph introducing a list
    for b in blocks:
        b["cand"] = None
        kind, text = b["kind"], b["text"]
        if kind == "heading" and not text.startswith("Sheet: ") and modal.search(text) and (
                "sheet" in b or len(text) > 90 or text.rstrip().endswith((".", ";", ","))):
            b["cand"] = "wording"                  # a spreadsheet row or a clause styled as a heading: a rule, not a title
            continue
        if kind == "heading" or b.get("is_header"):
            continue
        key = (b["doc"], b.get("heading"))
        if kind == "para" and BULLET.match(text):
            kind = "list"                          # "■  Incident & Problem Management: …" typed as a bullet
        if kind == "para":
            intro[key] = text
            if modal.search(text):
                b["cand"] = "wording"
        elif kind == "list":
            lead = intro.get(key, "")
            if modal.search(text):
                b["cand"] = "wording"
            elif not lead or modal.search(lead) or lead.rstrip().endswith(":"):
                b["cand"] = "list item"            # a list straight under a heading, or after "…shall:"
        elif kind == "row":
            cells = [c for c in b.get("cells", []) if c]
            if all(ID_LIKE.match(c) for c in cells):
                continue                           # an empty template row ("Q #: 7")
            if "sheet" in b and len(cells) > 1 and all(NUMBER.match(c) for c in cells[1:]):
                continue                           # a computed row: a label and numbers ("Subtotal — …: 0; 0; 0")
            if "sheet" in b:
                cols = matrix_columns(b.get("header"), config)
                if cols and _get(b, cols["requirement"]):
                    b["cand"] = "matrix row"
                    sec = _get(b, cols.get("section"))
                    b["matrix"] = {"ref": _get(b, cols.get("reference")), "section": sec, "section_ref": section_ref(sec)}
                else:
                    b["cand"] = "sheet row"
            elif b.get("header") is not None:      # docx/pdf table body row
                b["cand"] = "table row"
    return blocks


def _get(b, i):
    cells = b.get("cells") or []
    return cells[i].strip() if i is not None and i < len(cells) and cells[i] else None


def section_ref(value):
    """"S1.2 Submission" -> "1.2"; "§5.1.10" -> "5.1.10"; "A.3" -> "A.3"."""
    value = value or ""
    m = (re.search(r"(?:\bS|§)\s?(\d+(?:\.\d+)*)", value)
         or re.search(r"\b(\d+(?:\.\d+)+|[A-Z]\.\d+(?:\.\d+)*)\b", value))
    return m.group(1) if m else None
