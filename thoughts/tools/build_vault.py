#!/usr/bin/env python3
"""Build the "thoughts" Obsidian vault from metm.org/marco/thoughts.

The originals are classic Mac OS text files (Mac Roman), hard-wrapped at about
72 columns. Each becomes one note in Writings/, with properties from
tools/catalog.toml, the cover sheet kept verbatim in a box, and the text
re-flowed: wrapped prose lines are joined, short lines (verse, lists, the
printed directions) keep their line breaks. The originals are never changed.

    python3 tools/build_vault.py            # write new and changed notes
    python3 tools/build_vault.py --dry-run  # say what would change
    python3 tools/build_vault.py --check    # show the cover sheets that are cut

A note you have edited in Obsidian is not overwritten (tools/built.json keeps a
hash of what was last written); --force overwrites it anyway.
Needs only Python 3.11+.
"""

import argparse
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
TOOLS = VAULT / "tools"
WRAP = 55          # a prose line this long or longer was wrapped, not ended


def fname(title: str) -> str:
    """A file name Obsidian accepts, close to the title."""
    s = title.replace(": ", " – ").replace(":", " –").replace("/", "-").replace('"', "'")
    s = re.sub(r'[\\*<>|?#^\[\]]', "", s)
    return re.sub(r"\s+", " ", s).strip()


def read_source(path: Path) -> list[str]:
    text = path.read_bytes().decode("mac_roman").replace("\r\n", "\n").replace("\r", "\n")
    return text.split("\n")


def split_cover(lines: list[str], skip: int) -> tuple[list[str], list[str]]:
    """Take the first `skip` non-blank lines (the cover sheet) off the top."""
    cover, i = [], 0
    while i < len(lines) and len(cover) < skip:
        if lines[i].strip():
            cover.append(re.sub(r"\s+", " ", lines[i]).strip())
        i += 1
    return cover, lines[i:]


def escape(line: str) -> str:
    """Keep Markdown from reading the old plain text as markup."""
    if re.fullmatch(r"\s*[-=_*]{3,}\s*", line):
        return "---"                          # a separator line: make it a rule
    line = re.sub(r"^(\s*)(#+)", lambda m: m.group(1) + "\\" + m.group(2), line)
    line = re.sub(r"^(\s*)>", r"\1\\>", line)
    line = re.sub(r"#(?=[^\W\d_])", r"\\#", line)   # footnote '#' before a word is not a tag
    line = line.replace("[[", "\\[\\[")
    return line


def reflow(lines: list[str]) -> str:
    """Rebuild paragraphs from hard-wrapped lines.

    A block is lines between blank lines. A change between tab-indented and flush
    lines starts a new paragraph (the essays indent their own prose and set
    quotations flush, or the other way round). In prose, a line shorter than WRAP
    that ends a sentence ends the paragraph; any other line is joined to the next.
    In verse (most lines short) every line break is kept.
    """
    out, para = [], []

    def flush():
        if para:
            out.append("\n".join(para))
            para.clear()

    blocks, cur = [], []
    for raw in lines:
        if raw.strip():
            cur.append(raw.rstrip())
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)

    for block in blocks:
        segments, seg, indent = [], [], None
        for raw in block:
            ind = raw.startswith(("\t", "  "))
            if seg and ind != indent:
                segments.append(seg)
                seg = []
            seg.append(raw)
            indent = ind
        segments.append(seg)
        for seg in segments:
            texts = [re.sub(r"[ \t]+", " ", x).strip() for x in seg]
            longs = sum(len(x.expandtabs(8)) >= WRAP for x in seg)
            prose = longs * 2 >= len(seg)
            flush()
            if not prose:
                for t in texts:
                    if escape(t) == "---":
                        flush(); out.append("---")
                    else:
                        para.append(escape(t))
                flush()
                continue
            line = ""
            for raw, t in zip(seg, texts):
                if escape(t) == "---":
                    if line:
                        para.append(escape(line))
                    line = ""
                    flush(); out.append("---")
                    continue
                line = f"{line} {t}" if line else t
                short = len(raw.expandtabs(8)) < WRAP
                if short:
                    if re.search(r"[.!?:;\"')\]]$|#$", t):
                        para.append(escape(line))
                        flush()
                    else:
                        para.append(escape(line))
                    line = ""
            if line:
                para.append(escape(line))
            flush()
    flush()
    return "\n\n".join(quote_passages([p for p in out if p.strip()]))


CITATION = re.compile(r"(#|\(p+\.?\s*[\dxivl]+[^)]*\)|\(Folio[^)]*\))[\s.;,]*$", re.I)


def quote_passages(paras: list[str]) -> list[str]:
    """Set quotations as blockquotes, conservatively: a paragraph that follows one
    ending in a colon, and is either verse (several short lines) or ends with a
    citation (a footnote '#', a page reference)."""
    out = []
    for i, p in enumerate(paras):
        prev = paras[i - 1].rstrip() if i else ""
        verse = p.count("\n") >= 1 and all(len(x) < 70 for x in p.split("\n"))
        if prev.endswith(":") and p != "---" and (verse or CITATION.search(p)):
            p = "\n".join("> " + x for x in p.split("\n"))
        out.append(p)
    return out


def yaml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[]" if not v else "\n" + "\n".join(f"  - {yaml_value(x)}" for x in v)
    s = str(v)
    return json.dumps(s, ensure_ascii=False)


def frontmatter(props: dict) -> str:
    lines = ["---"]
    for k, v in props.items():
        if v is None or v == "" or (v == [] and k != "themes"):
            continue
        lines.append(f"{k}: {yaml_value(v)}")
    lines.append("---")
    return "\n".join(lines)


def text_note(t: dict, cat: dict, titles: dict, groups: dict) -> tuple[str, str]:
    src = Path(cat["source"]) / t["file"]
    cover, body_lines = split_cover(read_source(src), t.get("skip", 0))
    body = reflow(body_lines)
    words = len(re.findall(r"\w+", body))
    date = t.get("date")
    year = date.year if date else t.get("year")
    others = [titles[o["file"]] for o in groups.get(t.get("group"), []) if o is not t]
    tags = ["thoughts", t["type"]]
    if t["lang"] == "fr":
        tags.append("french")
    if t.get("course"):
        tags.append("coursework")
    props = {
        "title": t["title"],
        "type": t["type"],
        "date": date.isoformat() if date else None,
        "year": year,
        "dated": "on the page" if date else t.get("dated") if year else None,
        "era": t.get("era") or ("New Haven" if t.get("course") or year else None),
        "language": t["lang"],
        "course": t.get("course"),
        "teacher": t.get("teacher"),
        "section": t.get("section"),
        "people": t.get("people", []),
        "themes": [f"[[{th}]]" for th in t.get("themes", [])],
        "versions": [f"[[{fname(o)}]]" for o in others],
        "words": words,
        "source": f"metm.org/marco/thoughts/{t['file']}",
        "tags": tags,
    }
    parts = [frontmatter(props), "", f"# {t['title']}", ""]
    if t.get("note"):
        parts += [f"> [!note] About this file\n> {t['note']}", ""]
    if cover:
        parts += ["> [!quote]- Cover sheet\n" + "\n".join(f"> {escape(c)}  " for c in cover), ""]
    parts += [body, ""]
    return fname(t["title"]), "\n".join(parts)


THEME_BASE = """```base
filters:
  and:
    - file.inFolder("Writings")
    - file.hasLink(this.file)
views:
  - type: table
    name: Writings
    order:
      - file.name
      - year
      - type
      - course
      - words
    sort:
      - property: year
        direction: ASC
```"""


def theme_note(th: dict, members: list[dict]) -> str:
    parts = [frontmatter({"tags": ["theme"]}), "", f"# {th['name']}", "", th["about"], ""]
    if th.get("not"):
        parts += [f"*Left out:* {th['not']}", ""]
    parts += [f"{len(members)} texts. A text is in this theme when its `themes` property links here; "
              "add or remove the link to change that.", "", THEME_BASE, "", "## Notes", "", ""]
    return "\n".join(parts)


def home_note(cat: dict, counts: dict) -> str:
    themes = "\n".join(f"- [[{th['name']}]] ({counts[th['name']]}) — {th['about'].split(':')[0]}"
                       for th in cat["theme"])
    return f"""---
tags:
  - home
---

# Thoughts

Essays, notes, drafts and installation texts written mostly at Yale, 1992–1995,
copied from `metm.org/marco/thoughts` (the old site's folder of Mac-era text
files). Each file is one note in `Writings/`; the originals are untouched.

**How the notes were made.** The files were decoded from Mac Roman (so the
accents are right again) and the hard-wrapped lines joined into paragraphs.
Verse, lists and printed directions keep their line breaks. The cover sheet of
each paper (name, teacher, course, date) is kept as written in a folded
"Cover sheet" box, and its contents are also in the note's properties.

**Properties.** `type` (essay, draft, notes, extracts, transcription, letter,
installation-text, label, statement, exam, fragment, title-page), `date` when
the page gives one, otherwise `year` with `dated: estimated`, `course`,
`teacher`, `section`, `people` (the writers and artists the text is about),
`themes`, `versions` (other drafts or parts of the same piece), `words`,
`source`. Tags: `#thoughts` on every note (to tell them apart if they are ever
merged into another vault), the type, `#french`, `#coursework`.

**Themes** are strict: a text is in a theme only when the theme is what it is
about. {sum(not t.get('themes') for t in cat['text'])} texts have no theme; they are listed below.

{themes}

See also [[Courses]].

## All writings

```base
filters:
  and:
    - file.inFolder("Writings")
views:
  - type: table
    name: By date
    order:
      - file.name
      - year
      - type
      - language
      - themes
      - words
    sort:
      - property: year
        direction: ASC
      - property: date
        direction: ASC
  - type: table
    name: Not in any theme
    filters:
      and:
        - themes.isEmpty()
    order:
      - file.name
      - year
      - type
      - course
      - words
    sort:
      - property: year
        direction: ASC
  - type: table
    name: Own writing (not coursework)
    filters:
      and:
        - '!file.hasTag("coursework")'
    order:
      - file.name
      - year
      - type
      - themes
    sort:
      - property: year
        direction: ASC
```

## Not copied

Five files in the folder are empty: `Ba_labels_last.txt`, `Balabels-3.txt`,
`Beaux-arts_labels.txt`, `Beaux-arts_labels_2.txt`, `Document1.txt`.
`le_vent_a_djemila.html` is an old web page of half of
[[Le vent à Djémila — Space and Man]] with its accents destroyed, and
`index.html` is the folder listing.
"""


COURSES = """---
tags:
  - home
---

# Courses

The Yale courses the papers were written for, as named on their cover sheets.
Texts with no course are his own writing, transcriptions, or undated.

```base
filters:
  and:
    - file.inFolder("Writings")
    - '!course.isEmpty()'
views:
  - type: table
    name: By course
    order:
      - course
      - file.name
      - year
      - teacher
      - section
      - type
    sort:
      - property: course
        direction: ASC
      - property: date
        direction: ASC
```
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    cat = tomllib.loads((TOOLS / "catalog.toml").read_text())
    if args.check:
        for t in cat["text"]:
            cover, rest = split_cover(read_source(Path(cat["source"]) / t["file"]), t.get("skip", 0))
            first = next((x.strip() for x in rest if x.strip()), "")
            print(f"{t['file']:34} cover={cover}\n{'':34} text starts: {first[:70]}")
        return 0

    titles = {t["file"]: t["title"] for t in cat["text"]}
    groups: dict[str, list] = {}
    for t in cat["text"]:
        if t.get("group"):
            groups.setdefault(t["group"], []).append(t)
    counts = {th["name"]: 0 for th in cat["theme"]}
    for t in cat["text"]:
        for th in t.get("themes", []):
            counts[th] += 1

    names = [fname(t["title"]) for t in cat["text"]]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        sys.exit(f"Two texts would get the same file name: {dupes}")

    notes = {}
    for t in cat["text"]:
        name, content = text_note(t, cat, titles, groups)
        notes[f"Writings/{name}.md"] = content
    for th in cat["theme"]:
        notes[f"Themes/{th['name']}.md"] = theme_note(th, [t for t in cat["text"] if th["name"] in t.get("themes", [])])
    notes["Home.md"] = home_note(cat, counts)
    notes["Courses.md"] = COURSES

    state_path = TOOLS / "built.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    stats = {"new": 0, "updated": 0, "unchanged": 0, "kept (edited by you)": 0}
    for rel, content in notes.items():
        path = VAULT / rel
        digest = hashlib.sha1(content.encode()).hexdigest()
        if path.exists():
            current = hashlib.sha1(path.read_bytes()).hexdigest()
            if current == digest:
                stats["unchanged"] += 1
                state[rel] = digest
                continue
            if state.get(rel) != current and not args.force:
                stats["kept (edited by you)"] += 1
                print(f"kept, edited since last build: {rel}")
                continue
            stats["updated"] += 1
        else:
            stats["new"] += 1
        if args.dry_run:
            print(f"would write {rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        state[rel] = digest
    if not args.dry_run:
        state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True))
    print(", ".join(f"{v} {k}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
