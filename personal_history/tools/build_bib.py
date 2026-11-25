#!/usr/bin/env python3
"""Write Bibliography.md from tools/bibliography.yaml.

    python3 tools/build_bib.py

The page has an index of authors, then every text with its full reference, what was
guessed about it, and each note that mentions it, quoting the line where it does.
The quoted line is found with the regex given for that note in the YAML; a regex
that finds nothing is reported, so the YAML can be fixed.
"""

import re
import sys
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_nav import split, body_text  # noqa: E402

VAULT = Path(__file__).resolve().parent.parent
SRC = VAULT / "tools" / "bibliography.yaml"
OUT = VAULT / "Bibliography.md"
QUOTED = {"poem", "essay", "story", "article", "lecture"}


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def surname(e) -> str:
    a = e.get("author")
    return a.split(";")[0].split(",")[0].strip() if a else ""


def short_title(t: str) -> str:
    return t.split(": ")[0]


def heading(e) -> str:
    h = f"{surname(e)}, {short_title(e['title'])}" if e.get("author") else short_title(e["title"])
    return re.sub(r"[#^\[\]|:*\"%]", "", h).strip()


def sort_key(e):
    title = re.sub(r"^(the|a|an|le|la|les|l')\s*", "", fold(e["title"]))
    return (fold(surname(e)) or title, str(e.get("year", "")), title)


def citation(e) -> str:
    parts = []
    if e.get("author"):
        parts.append(e["author"].replace("; ", " and ").rstrip(".") + ".")
    t = e["title"]
    if t.startswith("("):
        parts.append(t + ".")  # a description, not a title
    else:
        parts.append(f"“{t}.”" if e.get("kind") in QUOTED else f"*{t}*.")
    if e.get("in"):
        if e.get("year") and str(e["year"]) not in e["in"]:
            parts.append(f"{e['year']}.")
        parts.append(f"In {e['in']}.")
    else:
        place_pub = ": ".join(x for x in (e.get("place"), e.get("publisher")) if x)
        pub = ", ".join(str(x) for x in (place_pub, e.get("year")) if x)
        if pub:
            parts.append(pub + ".")
    return " ".join(parts)


def clean(s: str) -> str:
    s = re.sub(r"</?u>|\*\*|`|^\s*(?:[-*•]|\d+\.)\s+|^>\s*(?:\[!\w+\]-?\s*)?", "", s)
    s = re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", s)
    return re.sub(r"\s+", " ", s).strip()


def excerpt(title: str, text: str, pat: str):
    """The line that matches: the transcription first, then the callout, then the title."""
    rx = re.compile(pat)
    lines = text.split("\n")
    passes = ([l for l in lines if not l.lstrip().startswith(">")],
              [l for l in lines if l.lstrip().startswith(">")], [title])
    for group in passes:
        for line in group:
            c = clean(line)
            m = rx.search(c)
            if m:
                a, b = max(0, m.start() - 90), min(len(c), m.end() + 140)
                if a > 0:
                    a = c.find(" ", a) + 1
                if b < len(c):
                    b = c.rfind(" ", 0, b)
                return ("…" if a > 0 else "") + c[a:b] + ("…" if b < len(c) else "")
    return None


def main():
    entries = yaml.safe_load(SRC.read_text())
    notes, problems, n_mentions = {}, [], 0
    for e in entries:
        for stem in e.get("mentions", {}):
            if stem not in notes:
                f = VAULT / f"{stem}.md"
                if not f.exists():
                    problems.append(f"{heading(e)}: no note {stem}")
                    continue
                parts = split(f.read_text())
                meta = yaml.safe_load(parts[0]) or {}
                title, text = body_text(parts[1])
                notes[stem] = (meta, title or stem, text)

    entries.sort(key=sort_key)
    heads = [heading(e) for e in entries]
    dup = {h for h in heads if heads.count(h) > 1}
    if dup:
        problems.append(f"duplicate headings: {dup}")

    out = ["# Bibliography", ""]
    blocks = []
    for e, h in zip(entries, heads):
        b = [f"### {h}", citation(e)]
        if e.get("note"):
            b.append(f"*Note:* {e['note']}")
        if e.get("guess"):
            b.append(f"*Guessed:* {e['guess']}")
        b.append("")
        ms = sorted((s for s in e.get("mentions", {}) if s in notes),
                    key=lambda s: (str(notes[s][0].get("date", "")), s))
        for stem in ms:
            meta, title, text = notes[stem]
            q = excerpt(title, text, e["mentions"][stem])
            if q is None:
                problems.append(f"{h}: /{e['mentions'][stem]}/ not found in {stem}")
            n_mentions += 1
            b.append(f"- [[{stem}|{title}]] · {meta.get('date', '')}" + (f" — “{q}”" if q else ""))
        blocks.append("\n".join(b))

    out += [f"{len(entries)} texts mentioned in the notes ({n_mentions} mentions), "
            "with the full reference of each and the lines of the notes that mention it. "
            "Details the notes don't give (publisher, year, sometimes the book itself) were "
            "filled in; anything uncertain is marked *Guessed*. Only texts are listed: films, "
            "artworks and talks Marco attended are not (published lectures are).", "",
            "Generated by `tools/build_bib.py` from `tools/bibliography.yaml`; edit the YAML, "
            "not this page.", "", "## Index of authors", ""]
    by_author = {}
    for e, h in zip(entries, heads):
        by_author.setdefault(e.get("author") or "(no author)", []).append((e, h))
    for a in sorted(by_author, key=lambda a: fold(a) if a != "(no author)" else "zzz"):
        links = ", ".join(f"[[#{h}|{short_title(e['title'])}]]" for e, h in by_author[a])
        out.append(f"- **{a}**: {links}")
    out += ["", "## Texts", "", "\n\n".join(blocks), ""]
    OUT.write_text("\n".join(out))

    print(f"{len(entries)} texts, {n_mentions} mentions -> {OUT.name}")
    for p in problems:
        print("  !", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
