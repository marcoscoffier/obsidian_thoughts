#!/usr/bin/env python3
"""Write Connections.html: every connection between two notes, with both notes side
by side, ordered by how far apart in time they were written.

    python3 tools/build_connections.py

Connections come from three places:
  - the labelled links drawn in life_timeline.canvas;
  - links from one note to another in the notes themselves (mostly "compare …" in the
    transcription notes), labelled with the sentence the link is in;
  - suggestions: notes a year or more apart that share uncommon themes (dashed).

Open Connections.html in a browser. It is self-contained apart from the page images,
which it loads from attachments/ when "Show the scanned page" is opened.
"""

import html
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_nav import split, body_text, unlink, as_list, image_path  # noqa: E402

VAULT = Path(__file__).resolve().parent.parent
OUT = VAULT / "Connections.html"
CANVAS = VAULT / "life_timeline.canvas"
MIN_SCORE = 6.0
PER_NOTE = 3
SKIP = {"AGENTS.md", "CLAUDE.md", "Scan index.md", "Bibliography.md"}


# ------------------------------------------------------------------ markdown -> html
def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"&lt;(/?u)&gt;", r"<\1>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r'<span class="wl" data-note="\1">\2</span>', s)
    s = re.sub(r"\[\[([^\]]+)\]\]", lambda m: f'<span class="wl" data-note="{m.group(1)}">'
               f'{m.group(1).split("/")[-1].replace("-", " ")}</span>', s)
    return s.replace("\\-", "-").replace("\\", "")


def render(text: str) -> tuple[str, str]:
    """The transcription and the transcription-notes callout, as HTML."""
    body, notes, para, items = [], [], [], []

    def flush():
        if para:
            body.append("<p>" + "<br>".join(para) + "</p>")
            para.clear()
        if items:
            body.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
            items.clear()

    for line in text.split("\n"):
        if line.startswith(">"):
            t = re.sub(r"^>\s?", "", line)
            if not re.match(r"\[!\w+\]", t):
                notes.append(inline(re.sub(r"^[-*]\s+", "• ", t)))
            continue
        if not line.strip():
            flush()
            continue
        if re.fullmatch(r"\s*-{3,}\s*", line):
            flush()
            body.append("<hr>")
            continue
        m = re.match(r"(#{1,6})\s+(.*)", line)
        if m:
            flush()
            body.append(f"<h4>{inline(m.group(2))}</h4>")
            continue
        m = re.match(r"\s*[-*•]\s+(.*)", line)
        if m:
            if para:
                flush()
            items.append(inline(m.group(1)))
            continue
        if items:
            flush()
        para.append(inline(line))
    flush()
    return "\n".join(body), "<br>".join(n for n in notes if n.strip())


# ------------------------------------------------------------------ data
def when(date) -> float:
    s = str(date or "")
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", s)
    if not m:
        return 0.0
    y, mo, d = int(m.group(1)), int(m.group(2) or 7), int(m.group(3) or 1)
    return y + (mo - 1) / 12 + (d - 1) / 365


def context(text: str, target: str, titles: dict) -> str:
    for line in text.split("\n"):
        if f"[[{target}" in line:
            c = re.sub(r"^>\s?|^\s*[-*]\s+", "", line)
            c = re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", lambda m: "→ " + (
                m.group(2) if m.group(1) else titles.get(m.group(2), m.group(2).replace("-", " "))), c)
            c = re.sub(r"[*`]|</?u>", "", c).strip()
            sentences = re.split(r"(?<=[.;])\s+", c)
            for s_ in sentences:
                if "→" in s_:
                    return s_[:220]
            return c[:220]
    return ""


def main():
    notes = {}
    for f in sorted(VAULT.glob("*.md")):
        if f.name in SKIP:
            continue
        parts = split(f.read_text())
        if not parts:
            continue
        meta = yaml.safe_load(parts[0]) or {}
        title, text = body_text(parts[1])
        notes[f.stem] = {"meta": meta, "title": title or f.stem, "text": text, "raw": parts[1]}

    conns = {}

    def add(a, b, label, source, color):
        if a not in notes or b not in notes or a == b:
            return
        if (when(notes[a]["meta"].get("date")), a) > (when(notes[b]["meta"].get("date")), b):
            a, b = b, a
        key = (a, b)
        if key in conns:
            if source == "timeline":  # the canvas label wins; keep the note's sentence too
                conns[key].update(label=label, source="timeline", color=color,
                                  also=conns[key]["label"])
            return
        conns[key] = {"a": a, "b": b, "label": label, "source": source, "color": color, "also": ""}

    titles = {k: v["title"] for k, v in notes.items()}
    canvas = json.loads(CANVAS.read_text())
    nodes = {n["id"]: n for n in canvas["nodes"]}
    for e in canvas["edges"]:
        fa, fb = nodes[e["fromNode"]].get("file", ""), nodes[e["toNode"]].get("file", "")
        add(Path(fa).stem, Path(fb).stem, e.get("label", ""), "timeline", e.get("color", ""))

    for stem, n in notes.items():
        for target in dict.fromkeys(re.findall(r"\[\[([^\]|#]+)", n["raw"])):
            if target in notes and target != stem:
                add(stem, target, context(n["raw"], target, titles), "notes", "")

    # Suggestions: notes a year or more apart that share uncommon themes. Each shared
    # theme scores log(notes / notes with that theme); pairs scoring MIN_SCORE+ are kept.
    themes = {k: {unlink(t) for t in as_list(v["meta"].get("themes"))} for k, v in notes.items()}
    df = Counter(t for ts in themes.values() for t in ts)
    idf = {t: math.log(len(notes) / c) for t, c in df.items()}
    stems, cands = sorted(notes), []
    for i, a in enumerate(stems):
        for b in stems[i + 1:]:
            if abs(when(notes[a]["meta"].get("date")) - when(notes[b]["meta"].get("date"))) < 1:
                continue
            shared = themes[a] & themes[b]
            score = sum(idf[t] for t in shared)
            if len(shared) >= 2 and score >= MIN_SCORE:
                cands.append((score, a, b, sorted(shared, key=lambda t: -idf[t])))
    per_note = Counter()  # at most PER_NOTE suggestions per note, the strongest first
    for score, a, b, shared in sorted(cands, reverse=True):
        if per_note[a] < PER_NOTE and per_note[b] < PER_NOTE and (a, b) not in conns:
            per_note[a] += 1
            per_note[b] += 1
            add(a, b, "Shared themes: " + ", ".join(shared), "themes", "")

    used = {c["a"] for c in conns.values()} | {c["b"] for c in conns.values()}
    out_notes = {}
    for stem in used:
        n, meta = notes[stem], notes[stem]["meta"]
        body, callout = render(n["text"])
        imgs = []
        for sc in as_list(meta.get("scan")):
            sc = str(sc)
            p = image_path(sc[len("photo-"):] if sc.startswith("photo-") else sc)
            if p:
                imgs.append(p)
        out_notes[stem] = {
            "t": n["title"], "d": str(meta.get("date", "")), "est": meta.get("dated") == "estimated",
            "w": round(when(meta.get("date")), 4), "era": unlink(meta.get("era", "")) if meta.get("era") else "",
            "th": [unlink(t) for t in as_list(meta.get("themes"))],
            "pp": [str(p) for p in as_list(meta.get("people"))],
            "body": body, "notes": callout, "img": imgs,
        }
    out_conns = sorted(conns.values(), key=lambda c: -(out_notes[c["b"]]["w"] - out_notes[c["a"]]["w"]))
    data = json.dumps({"notes": out_notes, "conns": out_conns}, ensure_ascii=False)
    page = TEMPLATE.replace("/*DATA*/null", data.replace("</", "<\\/"))
    OUT.write_text(page)
    k = Counter(c["source"] for c in out_conns)
    print(f"{len(out_conns)} connections ({k['timeline']} from the timeline canvas, {k['notes']} from "
          f"links in the notes, {k['themes']} suggested from shared themes) between "
          f"{len(out_notes)} notes -> {OUT.name}")


TEMPLATE = (Path(__file__).resolve().parent / "connections_template.html").read_text()

if __name__ == "__main__":
    sys.exit(main())
