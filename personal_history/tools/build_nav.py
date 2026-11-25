#!/usr/bin/env python3
"""Build the navigation pages of the personal_history vault.

    python3 tools/build_nav.py          # rewrite note properties and the nav pages
    python3 tools/build_nav.py --dry    # only report what would change

For every note in the vault root it:
  - maps `era` onto one of the canonical eras below (old names are aliases) and
    writes it as a link by path, e.g.  era: "[[Eras/Paris, Beaux-Arts|Paris, Beaux-Arts]]"
    (by path because some names repeat across folders: theme "japan", era "Japan");
  - writes each theme used by at least MIN_THEME notes as a link to its theme
    page (rarer themes stay plain text);
  - sets `subjects` (generated, don't edit by hand) from the themes, using
    FAMILIES and RULES below.
Then it regenerates Themes/, Eras/ and Subjects/ as reading pages: every note in
the theme, era or subject, in date order, with its transcription inline (images,
the page-image section and crop captions left out; the transcription-notes callout
folded). Each entry's title links to the note, and its scan pages are linked
beside the date, so the pages can be read straight through.

Only the `themes`, `era` and `subjects` lines of the frontmatter are rewritten;
everything else in a note is left as it is.
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent
SKIP = {"AGENTS.md", "CLAUDE.md", "Scan index.md"}
MIN_THEME = 3

# ------------------------------------------------------------------ eras
ERAS = {  # canonical name -> one-line description (date range is added automatically)
    "Yale, New Haven": "College years in New Haven, up to the summer of 1994.",
    "Summer 1994, Travel and Alps": "The road trip and the summer in France and the Alps (Tignes, Annecy, Mont Blanc).",
    "Final Semester Yale 1995": "Senior year at Yale: the thesis pieces, Ron Jones's lectures, the break-up with Katherine.",
    "DC, Post-College": "Washington DC after graduation: the NEA, Jackson, the letters to Katherine.",
    "Paris, Beaux-Arts": "Student at the École nationale supérieure des Beaux-Arts in Paris (from 1996).",
    "Japan": "The stay in Japan, September–December 1998 (Tokyo, Musabi, Miwa's family).",
    "New York 2005": "A new start in New York in 2005: the phone and dialog projects, almost-something.",
    "Present, Therapy Notes": "Recent notes.",
}
ERA_ALIASES = {
    "New Haven": "Yale, New Haven",
    "College / New Haven": "Yale, New Haven",
    "Yale / Retrospective": "Yale, New Haven",
    "New Haven / Summer Travel": "Summer 1994, Travel and Alps",
    "The Alps / Tignes": "Summer 1994, Travel and Alps",
    "French Alps": "Summer 1994, Travel and Alps",
    "French Alps (Tignes)": "Summer 1994, Travel and Alps",
    "Mountains / Alps": "Summer 1994, Travel and Alps",
    "Alps / Glacier": "Summer 1994, Travel and Alps",
    "Alps / Mont Blanc": "Summer 1994, Travel and Alps",
    "France / Retrospective Notes": "Summer 1994, Travel and Alps",
    "Summer 1994 (Away from New Haven)": "Summer 1994, Travel and Alps",
    "DC / Post-College": "DC, Post-College",
    "New Haven / Post-College": "DC, Post-College",
    "Paris / Beaux-Arts": "Paris, Beaux-Arts",
    "New York / 2005": "New York 2005",
    "Present / Therapy Notes": "Present, Therapy Notes",
}
ERA_OVERRIDE = {  # note stem -> era, where the era doesn't follow from the old label
    "1995-10-01_Labeling-an-Office-Building": "DC, Post-College",
}

# ------------------------------------------------------------------ subjects
P, M, T, L, S = ("Perception and Space", "Making Art", "Art Theory and the Art World",
                 "Language and Literature", "Sound and Music")
X, R, F, SELF, PL = ("Mind, Science and Systems", "Love and Relationships", "Family",
                     "Self", "Places and Cities")
SUBJECTS = {
    P: "Seeing, light, space and the instruments that change them.",
    M: "Pieces, proposals, studio work: installation, sculpture, painting, photography, video.",
    T: "Ideas about art, criticism, art history, the art world and culture at large.",
    L: "Reading, writing, poetry, French, language and signs.",
    S: "Sound, listening and music.",
    X: "Cognition, systems, technology, mathematics and science.",
    R: "Katherine, love, friendship, letters.",
    F: "Father, family, brothers, childhood.",
    SELF: "Feelings, fears, ambition, identity, the body, dreams.",
    PL: "Places, cities, travel, landscape and nature.",
}
FAMILIES = {
    P: "perception light space mirrors observation sky optics perspective framing turrell arnheim "
       "clouds gestalt color-theory illusion time invisibility scale space-vs-time stereoscopic-vision "
       "textures transparency visual-perception",
    M: "installation sculpture-ideas photography studio-practice drawing painting video sculpture "
       "painting-process craft land-art bricolage collage materiality dance gesture creativity "
       "painting-concepts painting-technique pixels alpine-painting creative-flow painting-practice project-list",
    T: "art-theory coursework criticism painting-theory art-history film mass-culture politics television "
       "aesthetics history modernism representation studio-critique abstraction economics meaning-in-art "
       "museums teaching",
    L: "french reading poetry language writing-process literature communication semiotics reading-list "
       "ekphrasis finnegans-wake imagination metaphor writing-style etymology fragments metaphor-and-metonymy "
       "quoting signs symbols writing-anxiety",
    S: "music sound sound-art notation recording sound-installation",
    X: "technology cognition systems play epistemology engineering internet knowledge art-vs-science "
       "geometry learning mathematics simplicity",
    R: "intimacy katherine friendship love letters commitment endings marriage-crisis marriage-distance "
       "address-book distance double-bind emotional-distance separation sexuality",
    F: "childhood-memory family father brotherhood",
    SELF: "memory solitude body self-criticism ambition fear identity vocation dreams ego gender mortality "
          "religion retrospective-self self-awareness social-alienation stereotypes synchronicity therapy "
          "athleticism coffee individuality individuation insecurity job-search privilege risk-taking shame "
          "vulnerability mountain-biking",
    PL: "japan city maps nature urbanism architecture flight travel yale-culture place-attachment public-space "
        "alps landscape tignes yale france wind",
}
FAMILY_OF = {t: fam for fam, ts in FAMILIES.items() for t in ts.split()}
RULES = [  # for themes not listed above: first matching pattern wins
    (M, r"paint|brush|palette|sculpt|drawing|sketch|portrait|calligraph|woodwork|art-making|collage|montage|"
        r"video-art|reworking|cubism|screens|flashlight|scientific-objects|pinhole"),
    (S, r"sound|music|acoustic|speech"),
    (F, r"father|family|childhood|sister|brother"),
    (R, r"katherine|marriage|romance|passion|love|intima|connection|shared|community|social|secre|stolen|"
        r"self-disclosure|self-revelation|mentorship"),
    (SELF, r"self|ego|shame|pride|fear|anxi|insecur|confiden|identity|personality|validation|ritual|rites|"
           r"masculin|sexism|body|running|climbing|hiking|skiing|mountaineer|dissociation|trapped|isolation|"
           r"uncertain|acceptance|adhd|emotional|class-guilt|education|intellectual|belonging|control|"
           r"boundaries|freud|dream|awe|perfume|sensitivity|travel-scars|activity|time-limits|rhodes"),
    (L, r"word|language|meta|metonymy|synecdoche|typography|note|notebook|writing|autofiction|stream|canon|"
        r"mytholog|naming|indexing|raw-thoughts|poetic|literature|space-vs-poetry"),
    (P, r"light|shadow|sun|optic|stereo|depth|percept|sensory|space|projection|anamorph|flat|mirror|water|"
        r"sea|tactile|immersion|face|innocent-eye|vertical|weight|gravity|big-dipper|3d|spatial|candle|"
        r"color|reference-frames|image-placement|viewing|innocent"),
    (PL, r"city|urban|america|paris|arles|annecy|notre-dame|fairhaven|saybrook|yale|travel|utopia|place|"
         r"museum-walks|cross-cultural"),
    (X, r"fractal|entropy|science|sensors|signals|interactiv|bateson|computer|structures|simultaneity|"
        r"mental-maps|originality|reproduction"),
    (T, r"art|museum|critique|picasso|diebenkorn|roden|turrell|theater|film|form-and|necessity|earthworks|"
        r"expressionism|western|chinese|yuag|collecting"),
]


def family_of(theme: str):
    if theme in FAMILY_OF:
        return FAMILY_OF[theme]
    for fam, pat in RULES:
        if re.search(pat, theme):
            return fam
    return None


# ------------------------------------------------------------------ helpers
def unlink(v) -> str:
    v = str(v).strip()
    m = re.fullmatch(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", v)
    return m.group(1).split("/")[-1] if m else v


def link(folder: str, name: str) -> str:
    """A link by path, so "japan" (theme) and "Japan" (era) can't be confused."""
    return f"[[{folder}/{name}|{name}]]"


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def q(s: str) -> str:
    return '"' + s.replace('"', '\\"') + '"'


def split(text: str):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    return text[4:end], text[end:]


def set_keys(front: str, new: dict) -> str:
    """Replace (or add) top-level keys in raw frontmatter text, keeping all other lines."""
    lines = front.split("\n")
    out, i, placed = [], 0, set()
    while i < len(lines):
        m = re.match(r"^([A-Za-z_][\w-]*):", lines[i])
        if m and m.group(1) in new:
            key = m.group(1)
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or lines[i].startswith("- ")):
                i += 1
            if new[key] is not None:
                out.append(new[key])
            placed.add(key)
            continue
        out.append(lines[i])
        i += 1
    for key, line in new.items():
        if key not in placed and line is not None:
            # put subjects right after themes, anything else at the end
            idx = next((k + 1 for k, l in enumerate(out) if l.startswith("themes:")), len(out))
            out.insert(idx, line)
    return "\n".join(out)


def body_text(rest: str) -> tuple[str, str]:
    """The note's title and its transcription, without images, the page-image
    section or crop captions. Headings are pushed down so they sit under the entry."""
    body = rest[len("\n---\n"):] if rest.startswith("\n---\n") else rest
    cut = re.search(r"\n---\s*\n+## Original Page", body)
    if cut:
        body = body[:cut.start()]
    title, out = "", []
    for line in body.strip("\n").split("\n"):
        if not title and line.startswith("# "):
            title = line[2:].strip()
            continue
        if re.fullmatch(r"\s*!\[\[[^\]]+\]\]\s*", line) or line.startswith("*Part of [["):
            continue
        if re.match(r"#{1,4} ", line):
            line = "###" + line[line.index(" "):] if line.startswith("# ") else "#" * 2 + line
        if re.match(r"> \[!\w+\](?!-)", line):
            line = re.sub(r"> \[!(\w+)\]", r"> [!\1]-", line, count=1)
        out.append(line)
    return title, "\n".join(out).strip("\n")


_IMAGES = None


def image_path(stem: str):
    """attachments/… path of the image with this name (any folder, any extension)."""
    global _IMAGES
    if _IMAGES is None:
        _IMAGES = {}
        for f in sorted((VAULT / "attachments").rglob("*")):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
                _IMAGES.setdefault(f.stem, f.relative_to(VAULT).as_posix())
    return _IMAGES.get(stem)


def page_links(meta) -> str:
    links = []
    for sc in as_list(meta.get("scan")):
        sc = str(sc)
        img = sc[len("photo-"):] if sc.startswith("photo-") else sc
        m = re.search(r"_p0*(\d+)$", img)
        label = f"p. {m.group(1)}" if m else img
        path = image_path(img)
        links.append(f"[[{path}|{label}]]" if path else label)
    return ", ".join(links)


def reading(sel, show_era: bool) -> str:
    parts = []
    for e in sel:
        f, meta = e["file"], e["meta"]
        title, text = body_text(e["body"])
        info = [str(meta.get("date", ""))]
        if meta.get("dated") == "estimated":
            info[0] += " (estimated)"
        if show_era and e["era"]:
            info.append(e["era"])
        if meta.get("notebook_page"):
            info.append(f"notebook p. {meta['notebook_page']}")
        pl = page_links(meta)
        if pl:
            info.append("scan " + pl)
        parts.append(f"## [[{f.stem}|{title or f.stem}]]\n*" + " · ".join(i for i in info if i)
                     + f"*\n\n{text}\n")
    return "\n---\n\n".join(parts)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    notes = []
    for f in sorted(VAULT.glob("*.md")):
        if f.name in SKIP:
            continue
        parts = split(f.read_text())
        if not parts:
            continue
        meta = yaml.safe_load(parts[0]) or {}
        notes.append((f, parts, meta))

    counts = Counter(unlink(t) for _, _, m in notes for t in as_list(m.get("themes")))
    linked = {t for t, n in counts.items() if n >= MIN_THEME}

    unknown_eras, unmapped, nosubject, changed = Counter(), Counter(), [], 0
    era_dates, subj_themes = defaultdict(list), defaultdict(set)
    entries = []
    for f, (front, rest), meta in notes:
        themes = [unlink(t) for t in as_list(meta.get("themes"))]
        era = unlink(meta.get("era", "")) if meta.get("era") else ""
        era = ERA_OVERRIDE.get(f.stem, ERA_ALIASES.get(era, era))
        if era and era not in ERAS:
            unknown_eras[era] += 1
        subjects = []
        for t in themes:
            fam = family_of(t)
            if fam is None:
                unmapped[t] += 1
            elif fam not in subjects:
                subjects.append(fam)
            if fam and t in linked:
                subj_themes[fam].add(t)
        if themes and not subjects:
            nosubject.append(f.name)
        if era in ERAS and meta.get("date"):
            era_dates[era].append(str(meta["date"]))
        new = {
            "themes": "themes: [" + ", ".join(q(link("Themes", t)) if t in linked else q(t) for t in themes) + "]"
                      if themes else None,
            "era": f"era: {q(link('Eras', era))}" if era in ERAS else (f"era: {era}" if era else None),
            "subjects": "subjects: [" + ", ".join(q(link("Subjects", s)) for s in subjects) + "]" if subjects else None,
        }
        entries.append({"file": f, "meta": meta, "body": rest, "era": era if era in ERAS else "",
                        "themes": [t for t in themes if t in linked], "subjects": subjects})
        new = {k: v for k, v in new.items() if v is not None or k == "subjects"}
        text = "---\n" + set_keys(front, new) + rest
        if text != f.read_text():
            changed += 1
            if not args.dry:
                f.write_text(text)

    print(f"{len(notes)} notes, {changed} {'would change' if args.dry else 'updated'}")
    print(f"{len(linked)} theme pages (themes used {MIN_THEME}+ times), {len(ERAS)} eras, {len(SUBJECTS)} subjects")
    if unknown_eras:
        print("eras not in ERAS (left as text):", dict(unknown_eras))
    if unmapped:
        print("themes with no subject:", ", ".join(sorted(unmapped)))
    if nosubject:
        print("notes with no subject:", ", ".join(nosubject))
    if args.dry:
        return

    for folder in ("Themes", "Eras", "Subjects"):
        d = VAULT / folder
        d.mkdir(exist_ok=True)
        for old in d.glob("*.md"):  # regenerate from scratch
            old.unlink()

    def order(e):  # by date; notes with the same date in notebook page order
        scans = [str(x) for x in as_list(e["meta"].get("scan"))]
        m = re.match(r"(.*)_p(\d+)", scans[0]) if scans else None
        part = re.search(rf"{re.escape(scans[0])}_part(\d+)", e["body"]) if scans else None
        return (str(e["meta"].get("date", "")), m.group(1) if m else "", int(m.group(2)) if m else 0,
                int(part.group(1)) if part else 0, e["file"].name)

    entries.sort(key=order)
    intro = ("in date order. Each title opens the full note; the page links open the scanned "
             "pages. Generated by `tools/build_nav.py`; don't edit by hand.")

    for t in sorted(linked):
        fam = family_of(t)
        sub = f'subject: {q(link("Subjects", fam))}\n' if fam else ""
        sel = [e for e in entries if t in e["themes"]]
        (VAULT / "Themes" / f"{t}.md").write_text(
            f"---\ntags:\n  - theme\n{sub}---\n\n# {t}\n\n"
            f"{len(sel)} notes, {intro}\n\n" + reading(sel, show_era=True))

    for era, desc in ERAS.items():
        sel = [e for e in entries if e["era"] == era]
        ds = sorted(str(e["meta"]["date"]) for e in sel if e["meta"].get("date"))
        span = "" if not ds else (f" {ds[0][:7]}." if ds[0][:7] == ds[-1][:7] else f" {ds[0][:7]} – {ds[-1][:7]}.")
        (VAULT / "Eras" / f"{era}.md").write_text(
            f"---\ntags:\n  - era\n---\n\n# {era}\n\n{desc}{span}\n\n"
            f"{len(sel)} notes, {intro}\n\n" + reading(sel, show_era=False))

    for s_, desc in SUBJECTS.items():
        ts = ", ".join(link("Themes", t) for t in sorted(subj_themes.get(s_, [])))
        sel = [e for e in entries if s_ in e["subjects"]]
        (VAULT / "Subjects" / f"{s_}.md").write_text(
            f"---\ntags:\n  - subject\n---\n\n# {s_}\n\n{desc}\n\nThemes: {ts}\n\n"
            f"{len(sel)} notes, {intro}\n\n" + reading(sel, show_era=True))
    print("pages written: Themes/, Eras/, Subjects/")


if __name__ == "__main__":
    sys.exit(main())
