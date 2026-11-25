#!/usr/bin/env python3
"""Write "Scan index.md": every page of every scanned notebook PDF in attachments/,
with the notes that were transcribed from it (from each note's `scan` field).

Pages with no note are listed too, so a rescan shows what was never transcribed.
Notes whose page is only a photo (scan: photo-...) and notes with no scan field are
listed at the end. Run it again after adding or replacing notes:

    python3 tools/scan_index.py
"""

import re
import subprocess
from collections import defaultdict
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
OUT = VAULT / "Scan index.md"


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    """Reads the simple YAML used here: `key: value`, `key: [a, b]`, and the block
    lists Obsidian writes when it saves a note (`key:` then `  - a` lines)."""
    fm = text[4:text.find("\n---", 4)]
    out, key = {}, None
    for line in fm.splitlines():
        item = re.match(r"\s+-\s+(.*)", line)
        if item and key:
            out[key].append(item.group(1).strip().strip("\"'"))
        elif ":" in line and not line.startswith(" "):
            key, v = line.split(":", 1)
            key = key.strip()
            v = v.split(" #")[0].strip()
            out[key] = v if v else []
    return out


def as_list(v) -> list[str]:
    if isinstance(v, list):
        return v
    v = v.strip()
    if v.startswith("["):
        return [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
    return [v.strip("\"'")] if v else []


def pdf_pages(pdf: Path) -> int:
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", info).group(1))


def main():
    by_page = defaultdict(list)          # "scan_1994_1_p024" -> [note names]
    written = {}                         # "scan_1994_1_p024" -> notebook page written on it
    photos, unscanned = [], []
    for f in sorted(VAULT.glob("*.md")):
        if f.name in ("AGENTS.md", "CLAUDE.md", OUT.name):
            continue
        meta = frontmatter(f.read_text())
        if not meta:
            continue
        scans = as_list(meta.get("scan", ""))
        if not scans:
            unscanned.append(f.stem)
        for s in scans:
            if s.startswith("photo-"):
                photos.append((f.stem, s[len("photo-"):]))
            else:
                by_page[s].append(f.stem)
                if meta.get("notebook_page") and isinstance(meta["notebook_page"], str) and len(scans) == 1:
                    written.setdefault(s, meta["notebook_page"])

    lines = ["# Scan index", "",
             "Every page of each scanned notebook, and the notes transcribed from it (from "
             "each note's `scan` field). Use it when a notebook is rescanned: the notes listed "
             "against a page are the ones to replace. Pages marked — have no note yet.",
             "", "Regenerate with `python3 tools/scan_index.py`.", ""]
    for pdf in sorted((VAULT / "attachments").glob("scan_journal_*.pdf")):
        name = "scan_" + pdf.stem[len("scan_journal_"):]
        n = pdf_pages(pdf)
        covered = sum(1 for k in range(1, n + 1) if by_page.get(f"{name}_p{k:03d}"))
        lines += [f"## {pdf.name}", "",
                  f"{n} pages; {covered} have notes, {n - covered} have none.", "",
                  "| PDF page | Written page no. | Notes |", "|---|---|---|"]
        for k in range(1, n + 1):
            key = f"{name}_p{k:03d}"
            notes = ", ".join(f"[[{x}]]" for x in by_page.get(key, [])) or "—"
            lines.append(f"| {k} | {written.get(key, '')} | {notes} |")
        lines.append("")
    if photos:
        lines += ["## Pages only photographed (not in any PDF)", "",
                  "These notes come from a photo of a page that is not in the scanned PDFs.", "",
                  "| Note | Photo |", "|---|---|"]
        lines += [f"| [[{n}]] | `{p}` |" for n, p in photos]
        lines.append("")
    if unscanned:
        lines += ["## Notes with no scanned page", ""]
        lines += [f"- [[{n}]]" for n in unscanned]
        lines.append("")
    OUT.write_text("\n".join(lines))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
