"""Parse every file of an RFP pack into blocks: the smallest pieces of text with an exact location.

    parse(path) -> Doc(name, kind, blocks, unread)       never raises; problems go in `unread`

A block is one paragraph, one table row or one spreadsheet row:
    {id, doc, kind: heading|para|list|row|cell, text, loc, section, heading, style, header}
`loc` is what a citation prints ("§5.1.2 ¶3", "table 4 row 7", "sheet Matrix row 12", "p. 14").
`section` is the clause number of the nearest heading ("5.1.2"), when there is one.

Formats: .docx, .xlsx/.xlsm, .pdf, .txt/.md. Anything else is reported as unread, never guessed at.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

SECTION = re.compile(r"^\s*(?:SECTION|APPENDIX|ANNEX|SCHEDULE|PART)?\s*([A-Z]?\d+(?:\.\d+)*|[A-Z](?:\.\d+)+|[A-Z])\b[.)]?\s",
                     re.I)
MIN_PAGE_TEXT = 20                      # a PDF page with less text than this was probably scanned


@dataclass
class Doc:
    name: str
    path: str
    kind: str                           # docx | xlsx | pdf | text | unsupported
    blocks: list = field(default_factory=list)
    unread: list = field(default_factory=list)      # [{"what", "why"}]
    stats: dict = field(default_factory=dict)


def section_of(heading_text):
    m = SECTION.match(heading_text or "")
    return m.group(1).rstrip(".") if m else None


def parse(path):
    path = Path(path)
    doc = Doc(path.name, str(path), "unsupported")
    if not path.exists():
        doc.unread.append({"what": path.name, "why": "file not found"})
        return doc
    ext = path.suffix.lower()
    try:
        if ext == ".docx":
            doc.kind = "docx"; _docx(path, doc)
        elif ext in (".xlsx", ".xlsm"):
            doc.kind = "xlsx"; _xlsx(path, doc)
        elif ext == ".pdf":
            doc.kind = "pdf"; _pdf(path, doc)
        elif ext in (".txt", ".md"):
            doc.kind = "text"; _text(path, doc)
        else:
            doc.unread.append({"what": path.name, "why": f"{ext or 'no extension'} files can't be read yet"})
    except Exception as e:                                    # corrupt, password-protected, truncated…
        doc.unread.append({"what": path.name, "why": f"could not be read ({type(e).__name__}: {str(e)[:120]})"})
    for b in doc.blocks:
        b["doc"] = doc.name
        b.setdefault("section", None)
    return doc


# ---------------------------------------------------------------- docx
def _docx(path, doc):
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    d = docx.Document(str(path))
    heading, section, n_in_section, tables = "", None, 0, 0
    for child in d.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(child, d)
            text = p.text.strip()
            style = p.style.name if p.style is not None else ""
            if not text or style.lower().startswith(("toc", "table of")):
                continue
            if style.startswith(("Heading", "Title")):
                heading, n_in_section = text, 0
                section = section_of(text) or section
                doc.blocks.append({"kind": "heading", "text": text, "loc": _sec_loc(section, text), "section": section,
                                   "heading": heading, "style": style})
                continue
            n_in_section += 1
            listed = p._p.pPr is not None and p._p.pPr.numPr is not None
            doc.blocks.append({"kind": "list" if listed or "List" in style else "para", "text": text,
                               "loc": f"{_sec_loc(section, heading)} ¶{n_in_section}", "section": section,
                               "heading": heading, "style": style})
        elif tag == "tbl":
            tables += 1
            rows = Table(child, d).rows
            header = None
            for r, row in enumerate(rows, 1):
                cells = _dedupe([c.text.strip() for c in row.cells])
                if not any(cells):
                    continue
                if header is None:
                    header = cells
                text = " | ".join(c for c in cells if c)
                doc.blocks.append({"kind": "row", "text": text, "loc": f"{_sec_loc(section, heading)} table {tables} row {r}",
                                   "section": section, "heading": heading, "header": header if r > 1 else None,
                                   "cells": cells})
    images = len(d.inline_shapes)
    doc.stats = {"tables": tables, "images": images}
    if images:
        doc.unread.append({"what": f"{images} image(s)", "why": "text inside images isn't read (diagrams, scanned pages)"})


def _sec_loc(section, heading):
    return f"§{section}" if section else (f"\"{heading[:40]}\"" if heading else "start")


def _dedupe(cells):
    """Merged cells repeat their text in python-docx; keep one copy."""
    out = []
    for c in cells:
        if not out or c != out[-1]:
            out.append(c)
    return out


# ---------------------------------------------------------------- xlsx
def _xlsx(path, doc):
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=False)
    hidden = []
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            hidden.append(ws.title)
        rows = [[_cell(v) for v in r] for r in ws.iter_rows(values_only=True)]
        header, heading = None, ws.title
        doc.blocks.append({"kind": "heading", "text": f"Sheet: {ws.title}", "loc": f"sheet \"{ws.title}\"",
                           "heading": ws.title, "sheet": ws.title})
        for r, cells in enumerate(rows, 1):
            filled = [c for c in cells if c]
            if not filled:
                continue
            if header is None and len(filled) >= 3 and all(len(c) < 60 for c in filled) and r <= 15:
                header = cells
                doc.blocks.append({"kind": "row", "text": " | ".join(filled), "loc": f"sheet \"{ws.title}\" row {r}",
                                   "heading": heading, "sheet": ws.title, "cells": cells, "header": None, "is_header": True})
                continue
            if len(filled) == 1 and header is not None and len(filled[0]) < 120 and re.search(r"[A-Za-z]{3}", filled[0]):
                heading = filled[0]                              # a section row inside the table
                section = section_of(heading.replace("—", " "))
                doc.blocks.append({"kind": "heading", "text": filled[0], "loc": f"sheet \"{ws.title}\" row {r}",
                                   "heading": heading, "section": section, "sheet": ws.title})
                continue
            if header:
                text = "; ".join(f"{(header[i] or f'col {i + 1}').replace(chr(10), ' ')}: {c}"
                                 for i, c in enumerate(cells) if c and i < len(header))
                text += "".join(f"; {c}" for c in cells[len(header):] if c)
            else:
                text = " | ".join(filled)
            doc.blocks.append({"kind": "row", "text": text, "loc": f"sheet \"{ws.title}\" row {r}", "heading": heading,
                               "sheet": ws.title, "cells": cells, "header": header})
    doc.stats = {"sheets": len(wb.worksheets), "hidden_sheets": hidden}


def _cell(v):
    if v is None:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d") if not getattr(v, "hour", 0) else v.strftime("%Y-%m-%d %H:%M")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


# ---------------------------------------------------------------- pdf
def _pdf(path, doc):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            doc.unread.append({"what": path.name, "why": "password-protected"})
            return
    empty, heading, section = [], "", None
    for n, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if len(text.strip()) < MIN_PAGE_TEXT:
            empty.append(n)
            continue
        for k, para in enumerate(p for p in re.split(r"\n\s*\n|(?<=[.:;])\n(?=[A-Z0-9(•\-–])", text) if p.strip()):
            para = re.sub(r"\s*\n\s*", " ", para).strip()
            if len(para) < 120 and section_of(para) and not para.endswith((".", ";", ",")):
                heading, section = para, section_of(para)
                doc.blocks.append({"kind": "heading", "text": para, "loc": f"p. {n}", "section": section, "heading": heading})
                continue
            doc.blocks.append({"kind": "para", "text": para, "loc": f"p. {n} ¶{k + 1}", "section": section, "heading": heading})
    doc.stats = {"pages": len(reader.pages)}
    if empty:
        doc.unread.append({"what": f"page(s) {_ranges(empty)}", "why": "no text layer (scanned?): needs OCR, not read"})


def _ranges(nums):
    out, start = [], None
    for i, n in enumerate(nums):
        if start is None:
            start = n
        if i + 1 == len(nums) or nums[i + 1] != n + 1:
            out.append(str(start) if start == n else f"{start}–{n}")
            start = None
    return ", ".join(out)


# ---------------------------------------------------------------- text
def _text(path, doc):
    heading, section = "", None
    for k, para in enumerate(p.strip() for p in re.split(r"\n\s*\n", path.read_text(errors="replace")) if p.strip()):
        line = para.lstrip("#").strip()
        if para.startswith("#") or (len(line) < 100 and section_of(line) and "\n" not in line):
            heading, section = line, section_of(line) or section
            doc.blocks.append({"kind": "heading", "text": line, "loc": _sec_loc(section, heading), "section": section,
                               "heading": heading})
        else:
            doc.blocks.append({"kind": "para", "text": para, "loc": f"{_sec_loc(section, heading)} ¶{k + 1}",
                               "section": section, "heading": heading})
