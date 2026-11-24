#!/usr/bin/env python3
"""Build the Papa slides vault from ~/Pictures/Papa. Safe to re-run.

The READMEs (and Super8_clips/clips.csv) are the source of truth: every run
rewrites the generated part of each note from them. What you write under
"## Notes" in any note is kept, as are properties the script doesn't manage,
your own tags, and theme tags on notes marked `themes_status: reviewed`.

    python3 tools/build_vault.py            # update the vault
    python3 tools/build_vault.py --dry-run  # show what would change
    python3 tools/build_vault.py --only Afghanistan   # just matching rolls/reels

Images are never copied: media/rolls/<roll> and media/films/<reel> are
symlinks into the source folder. Clip thumbnails (media/thumbs) are made
with ffmpeg once and then reused.
"""

import argparse
import hashlib
import csv
import json
import os
import re
import subprocess
import sys
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
NOTES = "## Notes"
# Properties the script owns; anything else in a note's frontmatter is yours and kept.
MANAGED = {
    "type", "roll", "reel", "title", "n", "count", "date", "year", "period", "image", "video",
    "file", "old_file", "box_caption", "box_label", "caption_source", "place_uncertain",
    "missing", "tags", "themes_status", "sort", "start", "end", "duration", "film_tags",
    "readme", "unlisted", "box", "places", "places_maybe", "country", "place_source",
}
OWN_TAG = re.compile(r"^(slide|roll|clip|reel|period/.*|theme/.*|place/.*)$")
STATE = VAULT / "tools" / "state.json"   # what the script last suggested, to spot your edits

stats = Counter()
warnings: list[str] = []


# ---------------------------------------------------------------- model

@dataclass
class Item:
    """One slide or one film clip."""
    n: int
    file: str                 # file name in the source folder
    media: str | None         # vault path of the image/video shown
    en: str = ""
    fr: str = ""
    old_file: str = ""
    box_caption: str = ""
    missing: bool = False
    title: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class Group:
    """One slide roll or one Super 8 reel."""
    kind: str                 # "roll" or "reel"
    src: Path
    name: str                 # note and folder name in the vault
    year: int | None
    quarter: str | None
    title_en: str = ""
    title_fr: str = ""
    sections_en: str = ""
    sections_fr: str = ""
    items: list[Item] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)   # box photos etc. (vault paths)
    unlisted: list[str] = field(default_factory=list)
    box_label: str = ""
    box_text: str = ""

    @property
    def date(self) -> str:
        if self.year is None:
            return "undated"
        return f"{self.year}-{self.quarter}" if self.quarter and self.quarter != "QX" else str(self.year)

    @property
    def folder(self) -> str:
        return f"{'Rolls' if self.kind == 'roll' else 'Films'}/{self.name}"

    @property
    def link(self) -> str:
        return f"{self.folder}/{self.name}"

    def sort(self, n: int = 0) -> str:
        q = self.quarter if self.quarter and self.quarter != "QX" else "Q0"
        return f"{self.year or 9999}-{q}-{self.src.name}-{n:03d}"


def parse_date(s: str) -> tuple[int | None, str | None, str]:
    m = re.match(r"(\d{4}|undated)(?:_(Q[1-4X]))?_?(.*)", s)
    if not m:
        return None, None, s
    year = None if m.group(1) == "undated" else int(m.group(1))
    return year, m.group(2), m.group(3)


# ---------------------------------------------------------------- READMEs

ENTRY = re.compile(r"^\*\*(?P<file>[^*]+?)\*\*\s*(?:\((?P<meta>.*?)\)\s*)?:\s*(?P<desc>.*)$")
SKIP_SECTION = re.compile(r"^(photos|order|proposed order|ordre|ordre proposé)\b", re.I)


def parse_readme(path: Path) -> tuple[str, str, dict[str, dict]]:
    """Title, the other sections as markdown, and the photo entries by file name."""
    if not path.exists():
        return "", "", {}
    title, intro, sections, cur = "", [], [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## "):
            cur = [line[3:].strip(), []]
            sections.append(cur)
        else:
            (cur[1] if cur else intro).append(line)
    entries, other = {}, []
    intro = [l for l in intro if "README" not in l]
    if any(l.strip() for l in intro):
        other.append("\n".join(intro).strip())
    for heading, body in sections:
        if heading.lower().startswith("photos"):
            last = None
            for l in body:
                m = ENTRY.match(l)
                if m:
                    meta = m.group("meta") or ""
                    old = re.search(r"`([^`]+)`", meta)
                    box = re.search(r"«\s*(.*?)\s*»", meta)
                    last = m.group("file").strip()
                    entries[last] = {"desc": m.group("desc").strip(),
                                     "old": old.group(1) if old else "",
                                     "box": box.group(1) if box else ""}
                elif l.strip() and last and not l.startswith("#"):
                    entries[last]["desc"] += " " + l.strip()
                else:
                    last = None
        elif not SKIP_SECTION.match(heading):
            text = "\n".join(body).strip()
            text = re.sub(r"^(#+) ", r"#\1 ", text, flags=re.M)   # demote: they sit under ###
            other.append(f"### {heading}\n\n{text}")
    return title, "\n\n".join(other), entries


def natural(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def is_extra(name: str) -> bool:
    return bool(re.match(r"(box|IMG_)", name, re.I))


def box_photos(d: Path, pictures: list[str]) -> list[str]:
    """Photos of the slide box (box_front.jpg first, then other box*/IMG_* images),
    leaving out exact copies (the phone's IMG_ original next to its box_front)."""
    extras = sorted((f for f in pictures if is_extra(f) and Path(f).suffix.lower() in IMAGE_EXT),
                    key=lambda f: (not f.lower().startswith("box_front"), natural(f)))
    seen, out = set(), []
    for f in extras:
        digest = hashlib.sha1((d / f).read_bytes()).hexdigest()
        if digest not in seen:
            seen.add(digest)
            out.append(f)
    return out


def load_roll(d: Path, cfg: dict) -> Group:
    year, q, _ = parse_date(d.name.removeprefix("Papa_-_"))
    g = Group("roll", d, d.name.removeprefix("Papa_-_").replace("_", " "), year, q)
    g.title_en, g.sections_en, en = parse_readme(d / "README.md")
    g.title_fr, g.sections_fr, fr = parse_readme(d / "README_fr.md")
    box = d / "box_text_original.md"
    g.box_text = box.read_text(encoding="utf-8").strip() if box.exists() else ""
    files = sorted((p.name for p in d.iterdir() if p.is_file()), key=natural)
    pictures = [f for f in files if Path(f).suffix.lower() in IMAGE_EXT | {".tif", ".tiff"}]
    media_root = f"media/rolls/{d.name}"
    g.extras = [f"{media_root}/{f}" for f in box_photos(d, pictures)]
    variant = cfg.get("variants", {}).get(d.name)

    if en:
        names = list(en)
        g.unlisted = [f for f in pictures if f not in en and not is_extra(f)]
    else:
        names = [f for f in pictures if not is_extra(f)]
        if names:
            warnings.append(f"{d.name}: no README, {len(names)} slides without captions")
    for i, f in enumerate(names, 1):
        e, efr = en.get(f, {}), fr.get(f, {})
        m = re.match(r"(\d+)_", f) or re.search(r"(\d+)\.\w+$", f)
        n = int(m.group(1)) if m else i
        shown = f
        if variant:
            alt = variant.format(stem=Path(f).stem)
            if (d / alt).exists():
                shown = alt
            else:
                warnings.append(f"{d.name}: no {alt}, showing the scan")
        exists = (d / f).exists()
        if not exists:
            warnings.append(f"{d.name}: README lists {f}, which isn't in the folder")
        displayable = Path(shown).suffix.lower() in IMAGE_EXT
        g.items.append(Item(n, f, f"{media_root}/{shown}" if exists and displayable else None,
                            en=e.get("desc", ""), fr=efr.get("desc", ""), old_file=e.get("old", ""),
                            box_caption=e.get("box", ""), missing=not exists,
                            extra={"undisplayable": exists and not displayable}))
    return g


def load_reels(clips_dir: Path) -> list[Group]:
    csv_path = clips_dir / "clips.csv"
    if not csv_path.exists():
        return []
    rows = defaultdict(list)
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["keep"].strip().lower() == "yes":
                rows[r["video"]].append(r)
    groups = []
    for video, clips in rows.items():
        d = clips_dir / video
        year, q, rest = parse_date(video)
        label = re.sub(r"_?\d{7}-\w+$", "", rest).replace("_", " ").strip()
        reel_id = re.search(r"(\d{7}-\w+)$", video)
        name = " ".join(x for x in [str(year) if year else "undated", q if year else None, "Super 8",
                                    label, reel_id.group(1) if reel_id else None] if x)
        g = Group("reel", d, name, year, q)
        g.box_label = clips[0].get("box_label", "")
        g.title_en = f"Super 8 film: {g.box_label}" if g.box_label else "Super 8 film"
        box_txt = d / "box.txt"
        g.box_text = box_txt.read_text(encoding="utf-8", errors="replace").strip() if box_txt.exists() else ""
        if (d / "box.jpg").exists():
            g.extras = [f"media/films/{video}/box.jpg"]
        for r in sorted(clips, key=lambda r: int(r["clip"])):
            rel = Path(r["file"]).name
            exists = (d / rel).exists()
            if not exists:
                warnings.append(f"{video}: clips.csv lists {rel}, which isn't in the folder")
            g.items.append(Item(int(r["clip"]), rel, f"media/films/{video}/{rel}" if exists else None,
                                en=r["description"].strip(), title=r["title"].strip(), missing=not exists,
                                extra={"start": r["start_tc"], "end": r["end_tc"],
                                       "duration": float(r["duration"] or 0),
                                       "film_tags": [t.strip() for t in r["tags"].split(",") if t.strip()]}))
        groups.append(g)
    return groups


# ---------------------------------------------------------------- periods and themes

def slug(s: str) -> str:
    import unicodedata
    s = s.lower().replace("–", "-").replace("ø", "o").replace("æ", "ae").replace("ß", "ss")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def period_of(g: Group, cfg: dict) -> str | None:
    if g.year is None:
        return None
    for p in cfg.get("periods", []):
        lo, hi = p["years"]
        if lo <= g.year <= hi and (not p.get("match") or re.search(p["match"], g.src.name)):
            return p["name"]
    return None


def words_rx(words: list[str]):
    words = sorted(words, key=len, reverse=True)
    return re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in words) + r")(?![\w-])", re.I) if words else None


@dataclass
class Themes:
    rules: list          # (name, words_rx, [together groups of rx], rolls_rx, unless_rx, starts_rx)
    background: re.Pattern | None
    ignore: re.Pattern | None = None


def compile_themes(cfg: dict) -> Themes:
    rules = []
    for t in cfg.get("themes", []):
        together = [[words_rx([w]) for w in grp] for grp in t.get("together", [])]
        rules.append((t["name"], words_rx(t.get("words", [])), together,
                      re.compile(t["rolls"], re.I) if t.get("rolls") else None, words_rx(t.get("unless", [])),
                      re.compile(rf"\s*(?:{t['starts']})\b", re.I) if t.get("starts") else None))
    bg = cfg.get("background")
    return Themes(rules, re.compile(rf"\b({bg})\b", re.I) if bg else None, words_rx(cfg.get("ignore", [])))


def themes_for(caption: str, names: str, themes: Themes) -> list[str]:
    """Themes of one slide or clip. `names` is its file name, title and tags: words
    there describe the main subject, so they count wherever they appear. In the
    caption, a word only counts in a sentence that isn't about the background."""
    names = re.sub(r"[_\-]+", " ", names)
    if themes.ignore:
        caption, names = themes.ignore.sub(" ", caption), themes.ignore.sub(" ", names)
    sentences = re.split(r"(?<=[.!;])\s+", caption)
    out = []
    for name, rx, together, _, unless, starts in themes.rules:
        if unless and (unless.search(caption) or unless.search(names)):
            continue
        hit = bool(rx and rx.search(names))
        hit = hit or bool(rx and any(rx.search(s) and not (themes.background and themes.background.search(s))
                                     for s in sentences))
        hit = hit or any(all(w.search(caption) for w in grp) for grp in together)
        hit = hit or bool(starts and starts.match(caption))
        if hit:
            out.append(name)
    return out


def roll_themes(g: Group, themes: Themes) -> list[str]:
    return [name for name, _, _, rolls, *_ in themes.rules if rolls and rolls.search(g.src.name)]


# ---------------------------------------------------------------- places

def norm(s: str) -> str:
    return re.sub(r"[_\-\s]+", " ", s.lower()).strip()


HEDGE = re.compile(r"\b(possibly|perhaps|probably|maybe|likely|might|may be|could be|seems?|"
                   r"appears? to be|looks (very much |a lot |rather )?like|resembl\w*)\b", re.I)


@dataclass
class Gazetteer:
    entries: list        # (name, country, is_country, caption_rx, names_rx)

    @classmethod
    def load(cls, path: Path) -> "Gazetteer":
        if not path.exists():
            return cls([])
        cfg = tomllib.loads(path.read_text(encoding="utf-8"))
        exact = set(cfg.get("exact", []))
        entries = []

        def add(name, country, is_country, alias):
            cap = re.compile(r"(?<![\w-])" + re.escape(alias) + r"(?![\w-])")
            low = None if alias in exact else re.compile(r"(?<!\w)" + re.escape(norm(alias)) + r"(?!\w)")
            entries.append((name, country, is_country, cap, low))

        for country, aliases in cfg.get("countries", {}).items():
            for a in aliases:
                add(country, country, True, a)
        for country, places in cfg.get("places", {}).items():
            for name, aliases in places.items():
                for a in aliases:
                    add(name, country, False, a)
        return cls(entries)

    def hedged(self, text: str) -> set[str]:
        """Places a text only ever names uncertainly ("Mazar-i-Sharif?")."""
        found, _ = self.find(text, "")
        return {n for n, certain in found.items() if not certain}

    def find(self, caption: str, names: str, hedged: set[str] = frozenset()) -> tuple[dict[str, bool], list[str]]:
        """Places named ({name: certain}) and countries, from a caption and file names.
        A place only in the file names is uncertain if it's in `hedged`."""
        in_caption: dict[str, bool] = {}
        in_names: dict[str, None] = {}      # ordered, so every run gives the same order
        country_of = {}
        names_n = norm(names)
        for name, country, is_country, cap, low in self.entries:
            country_of[name] = (country, is_country)
            for m in cap.finditer(caption):
                after = caption[m.end():m.end() + 6]
                before = re.split(r"[.!;\n]", caption[max(0, m.start() - 120):m.start()])[-1]
                certain = not re.match(r"\s*(\(\s*\?\s*\)|\?)", after) and not HEDGE.search(before)
                in_caption[name] = in_caption.get(name, False) or certain
            if low and low.search(names_n):
                in_names[name] = None
        found = dict(in_caption)
        for name in in_names:
            if name not in in_caption:
                found[name] = name not in hedged
        places = {n: c for n, c in found.items() if not country_of[n][1]}
        countries = []
        for n in found:
            c = country_of[n][0]
            if c and c not in countries:
                countries.append(c)
        return places, countries


# ---------------------------------------------------------------- frontmatter

def split_note(text: str) -> tuple[str, str, str]:
    """(frontmatter, generated body, notes section)."""
    fm, body = "", text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            fm, body = text[4:end], text[end + 5:]
    m = re.search(r"^## Notes[ \t]*$", body, re.M)
    notes = body[m.start():] if m else ""
    return fm, body[:m.start()] if m else body, notes


def parse_fm(fm: str) -> dict[str, tuple[list[str], object]]:
    out, key = {}, None
    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
        if m:
            key, v = m.group(1), m.group(2).strip()
            if v.startswith("[") and v.endswith("]"):
                v = [unquote(x) for x in v[1:-1].split(",") if x.strip()]
            elif v == "":
                v = []
            else:
                v = unquote(v)
            out[key] = ([line], v)
        elif key:
            out[key][0].append(line)
            li = re.match(r"^\s*-\s*(.*)$", line)
            if li and isinstance(out[key][1], list):
                out[key][1].append(unquote(li.group(1)))
    return out


def unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        try:
            return json.loads(s) if s[0] == '"' else s[1:-1].replace("''", "'")
        except json.JSONDecodeError:
            return s[1:-1]
    return s


def emit(key: str, v) -> str:
    if isinstance(v, bool):
        return f"{key}: {'true' if v else 'false'}"
    if isinstance(v, (int, float)):
        return f"{key}: {v}"
    if isinstance(v, list):
        return f"{key}:" + "".join(f"\n  - {json.dumps(x, ensure_ascii=False)}" for x in v) if v else f"{key}: []"
    return f"{key}: {json.dumps(str(v), ensure_ascii=False)}"


def write_note(path: Path, props: dict, body: str, dry: bool, keep_theme_tags_if_reviewed=True):
    """Writes the generated part of a note, keeping the user's part."""
    old_fm, notes = {}, f"{NOTES}\n\n"
    existed = path.exists()
    if existed:
        fm, _, old_notes = split_note(path.read_text(encoding="utf-8"))
        old_fm = parse_fm(fm)
        if old_notes:
            notes = old_notes
    tags = list(props.get("tags", []))
    if "tags" in old_fm and isinstance(old_fm["tags"][1], list):
        old_tags = [t.lstrip("#") for t in old_fm["tags"][1]]
        reviewed = old_fm.get("themes_status", ([], ""))[1] == "reviewed"
        if reviewed and keep_theme_tags_if_reviewed:
            tags = [t for t in tags if not t.startswith("theme/")] + [t for t in old_tags if t.startswith("theme/")]
        tags += [t for t in old_tags if not OWN_TAG.match(t) and t not in tags]
    props["tags"] = list(dict.fromkeys(tags))
    if "themes_status" in props and "themes_status" in old_fm and old_fm["themes_status"][1]:
        props["themes_status"] = old_fm["themes_status"][1]
    lines = [emit(k, v) for k, v in props.items() if v is not None and v != ""]
    lines += ["\n".join(raw) for k, (raw, _) in old_fm.items() if k not in MANAGED]
    text = "---\n" + "\n".join(lines) + "\n---\n" + body.rstrip() + "\n\n" + notes
    if existed and path.read_text(encoding="utf-8") == text:
        stats["unchanged"] += 1
        return
    stats["updated" if existed else "new"] += 1
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def create_once(path: Path, text: str, dry: bool):
    if path.exists():
        return
    stats["new"] += 1
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- note bodies

def callout(kind: str, title: str, text: str, fold: str = "") -> str:
    lines = text.strip().splitlines() or [""]
    return f"> [!{kind}]{fold} {title}\n" + "\n".join(f"> {l}" if l.strip() else ">" for l in lines)


def bilingual(en: str, fr: str, fold: str = "") -> str:
    parts = []
    if en:
        parts.append(callout("en", "English", en, fold))
    if fr:
        parts.append(callout("fr", "Français", fr, fold))
    elif en:
        parts.append(callout("fr", "Français", "*Pas encore de texte en français.*", fold))
    return "\n\n".join(parts)


def item_name(it: Item, g: Group) -> str:
    if g.kind == "reel":
        return f"{it.n:02d} {re.sub(r'[\\/:#^|\[\]]', ' ', it.title or 'clip').strip()}"
    return Path(it.file).stem.replace("_", " ")


def cards_base(filters: list[str], name: str, image: str = "note.image", aspect: float = 0.75,
               order=("file.name",)) -> str:
    f = "\n".join(f"    - '{x}'" for x in filters)
    o = "\n".join(f"      - {x}" for x in order)
    return (f"```base\nfilters:\n  and:\n{f}\nviews:\n  - type: cards\n    name: {name}\n    order:\n{o}\n"
            f"    sort:\n      - property: sort\n        direction: ASC\n    image: {image}\n"
            f"    imageFit: contain\n    imageAspectRatio: {aspect}\n    cardSize: 220\n```")


def item_texts(it: Item) -> tuple[str, str]:
    """(caption text, name text) of a slide or clip, for themes and places."""
    caption = " ".join(x for x in [it.en, it.box_caption and f"« {it.box_caption} »"] if x)
    names = " ".join([it.file.rsplit(".", 1)[0], it.title, " ".join(it.extra.get("film_tags", []))])
    return caption, names


def group_hedged(g: Group, gaz: Gazetteer) -> set[str]:
    """Places the roll's README names only with a "?" (in captions and notes)."""
    return gaz.hedged("\n".join([g.sections_en] + [it.en for it in g.items]))


def group_places(g: Group, gaz: Gazetteer) -> tuple[dict[str, bool], list[str]]:
    return gaz.find("\n".join([g.title_en, g.box_text if g.kind == "roll" else "", g.box_label]),
                    g.src.name.removeprefix("Papa_-_"))


def place_info(caption, names, gaz: Gazetteer, roll_places, roll_countries, hedged=frozenset()):
    places, countries = gaz.find(caption, names, hedged)
    source = "caption" if places else None
    if not places and len(roll_places) == 1:
        places, source = dict(roll_places), "roll"
    if not countries and len(roll_countries) == 1:
        countries = list(roll_countries)
    return ([p for p, c in places.items() if c], [p for p, c in places.items() if not c], countries, source)


def plink(name: str) -> str:
    return f"[[Places/{name}|{name}]]"


def link_name(x: str) -> str:
    """'[[Places/Kabul|Kabul]]' -> 'Kabul'; plain text stays as it is."""
    m = re.match(r"\[\[(?:[^|\]]*/)?([^|\]]+)(?:\|[^\]]*)?\]\]", x.strip())
    return m.group(1) if m else x.strip()


def place_line(final: dict, source: str | None, label: str = "Place") -> str:
    bits = [x for x in final["places"]] + [f"{x} (?)" for x in final["places_maybe"]]
    if not bits and not final["country"]:
        return ""
    line = f"📍 {label}: " + (", ".join(bits) if bits else "")
    if final["country"]:
        line += (" · " if bits else "") + ", ".join(final["country"])
    if source == "roll":
        line += " *(from the roll's title)*"
    return line


def old_values(path: Path) -> dict | None:
    if not path.exists():
        return None
    return {k: v for k, (_, v) in parse_fm(split_note(path.read_text(encoding="utf-8"))[0]).items()}


def as_list(v) -> list:
    if v is None or v == "":
        return []
    return [v] if isinstance(v, str) else list(v)


def reconcile(key: str, generated: list, old: dict | None, last: dict | None) -> list:
    """The script's value, unless you changed what it wrote last time."""
    if old is None or last is None or key not in last:
        return generated
    current = as_list(old.get(key))
    return current if sorted(current) != sorted(last[key]) else generated


def reconcile_themes(computed: list, old: dict | None, last: dict | None) -> list:
    """Theme tags: the script's guesses, minus any you removed, plus any you added."""
    if old is None:
        return computed
    current = [t.lstrip("#") for t in as_list(old.get("tags")) if t.lstrip("#").startswith("theme/")]
    # Without a record (notes made before state.json existed), take the note's tags
    # as what the script wrote, so tags the stricter rules no longer give are dropped.
    previous = last["themes"] if last and "themes" in last else current
    removed = set(previous) - set(current)
    return [t for t in computed if t not in removed] + [t for t in current if t not in previous]


def build_group(g: Group, cfg: dict, themes: Themes, gaz: Gazetteer, state: dict, new_state: dict,
                dry: bool, thumbs: bool):
    period = period_of(g, cfg)
    period_link = f"[[Periods/{period}]]" if period else None
    period_tag = [f"period/{slug(period)}"] if period else []
    folder = VAULT / g.folder
    item_kind = "slide" if g.kind == "roll" else "clip"

    # Rename notes whose file was renamed in the source (matched by number).
    by_n = {}
    if folder.exists():
        for p in folder.glob("*.md"):
            if p.stem == g.name:
                continue
            props = parse_fm(split_note(p.read_text(encoding="utf-8"))[0])
            try:
                by_n[int(props.get("n", ([], ""))[1])] = p
            except (TypeError, ValueError):
                pass
    names, renamed = {}, {}
    for it in g.items:
        names[it.n] = item_name(it, g)
        old = by_n.pop(it.n, None)
        new = folder / f"{names[it.n]}.md"
        if old and old != new and not new.exists():
            stats["renamed"] += 1
            renamed[it.n] = old
            if not dry:
                old.rename(new)
    for p in by_n.values():   # notes whose slide or clip is gone: keep, mark missing
        text = p.read_text(encoding="utf-8")
        if "\nmissing: true" not in text:
            stats["marked missing"] += 1
            if not dry:
                p.write_text(text.replace("\n---\n", "\nmissing: true\n---\n", 1), encoding="utf-8")

    roll_places, roll_countries = group_places(g, gaz)
    hedged = group_hedged(g, gaz)
    agg = {"places": [], "places_maybe": [], "country": []}
    for i, it in enumerate(g.items):
        path = folder / f"{names[it.n]}.md"
        if dry and not path.exists():
            path = next((p for n, p in renamed.items() if n == it.n), path)
        old = old_values(path)
        last = state.get(f"{g.src.name}#{it.n}")
        caption, item_names = item_texts(it)
        computed = [f"theme/{slug(t)}" for t in themes_for(caption, item_names, themes)]
        theme_tags = reconcile_themes(computed, old, last)
        sure, maybe, countries, source = place_info(caption, item_names, gaz, roll_places, roll_countries, hedged)
        gen = {"places": [plink(p) for p in sure], "places_maybe": [plink(p) for p in maybe],
               "country": [plink(c) for c in countries]}
        final = {k: reconcile(k, v, old, last) for k, v in gen.items()}
        new_state[f"{g.src.name}#{it.n}"] = {"themes": computed, **gen}
        place_tags = [f"place/{slug(link_name(x))}" for k in final for x in final[k]]
        for k in final:
            agg[k] += [x for x in final[k] if x not in agg[k]]
        image = it.media
        if g.kind == "reel" and it.media and thumbs:
            image = make_thumb(g, it, dry)
        props = {
            "type": item_kind,
            ("roll" if g.kind == "roll" else "reel"): f"[[{g.link}|{g.name}]]",
            "title": it.title or None,
            "n": it.n,
            "date": g.date,
            "year": g.year,
            "period": period_link,
            "image": f"[[{image}]]" if image else None,
            "video": f"[[{it.media}]]" if g.kind == "reel" and it.media else None,
            "file": it.file,
            "old_file": it.old_file or None,
            "box_caption": it.box_caption or None,
            "start": it.extra.get("start"),
            "end": it.extra.get("end"),
            "duration": it.extra.get("duration"),
            "film_tags": it.extra.get("film_tags"),
            "caption_source": ("readme" if it.en else "none") if g.kind == "roll" else "clips.csv",
            "places": final["places"] or None,
            "places_maybe": final["places_maybe"] or None,
            "country": final["country"] or None,
            "place_source": source if (final["places"] or final["places_maybe"]) else None,
            "missing": True if it.missing else None,
            "themes_status": "auto",
            "sort": g.sort(it.n),
            "tags": [item_kind] + period_tag + theme_tags + place_tags,
        }
        parts = []
        if it.media:
            parts.append(f"![[{it.media}]]")
        elif it.extra.get("undisplayable"):
            parts.append(f"*{it.file} is a TIFF, which Obsidian can't display.*")
        elif it.missing:
            parts.append(f"*{it.file} is no longer in the source folder.*")
        where = place_line(final, source)
        if where:
            parts.append(where)
        if it.box_caption:
            parts.append(f"Box caption: « {it.box_caption} »")
        if g.kind == "reel":
            parts.append(f"{it.extra['start']} – {it.extra['end']} ({it.extra['duration']:.0f} s)")
        if it.en or it.fr:
            parts.append(bilingual(it.en, it.fr))
        else:
            parts.append("*No caption yet.*")
        nav = [f"[[{g.link}|{g.name}]] · {item_kind} {i + 1} of {len(g.items)}"]
        if i > 0:
            nav.append(f"[[{g.folder}/{names[g.items[i - 1].n]}|← previous]]")
        if i + 1 < len(g.items):
            nav.append(f"[[{g.folder}/{names[g.items[i + 1].n]}|next →]]")
        parts.append(" · ".join(nav))
        write_note(path, props, "\n\n".join(parts), dry)

    # The roll or reel note itself.
    # Roll places: what its title or box names, plus what its slides name.
    gen = {"places": [plink(p) for p, c in roll_places.items() if c],
           "places_maybe": [plink(p) for p, c in roll_places.items() if not c],
           "country": [plink(c) for c in roll_countries]}
    for k in gen:
        gen[k] += [x for x in agg[k] if x not in gen[k]]
    gen["places_maybe"] = [x for x in gen["places_maybe"] if x not in gen["places"]]
    note = VAULT / f"{g.link}.md"
    old, last = old_values(note), state.get(f"{g.src.name}#roll")
    final = {k: reconcile(k, v, old, last) for k, v in gen.items()}
    new_state[f"{g.src.name}#roll"] = gen
    props = {
        "type": g.kind,
        "title": g.title_en or g.name,
        "date": g.date,
        "year": g.year,
        "period": period_link,
        "count": len(g.items),
        "box_label": g.box_label or None,
        "readme": bool(g.title_en) if g.kind == "roll" else None,
        "unlisted": len(g.unlisted) or None,
        # Cards show the first slide; the box photo is in `box` and at the top of the note.
        "image": (f"[[{g.items[0].media}]]" if g.kind == "roll" and g.items and g.items[0].media
                  else f"[[{g.extras[0]}]]" if g.extras else None),
        "box": f"[[{g.extras[0]}]]" if g.extras else None,
        "places": final["places"] or None,
        "places_maybe": final["places_maybe"] or None,
        "country": final["country"] or None,
        "sort": g.sort(),
        "tags": [g.kind] + period_tag + [f"theme/{slug(t)}" for t in roll_themes(g, themes)]
                + [f"place/{slug(link_name(x))}" for k in final for x in final[k]],
    }
    parts = [f"# {g.title_en or g.name}"]
    if g.title_fr and g.title_fr != g.title_en:
        parts.append(callout("fr", "Français", f"**{g.title_fr}**"))
    parts.append(f"{g.date} · {len(g.items)} {item_kind}s" + (f" · [[Periods/{period}|{period}]]" if period else "")
                 + " · [[Timeline]]")
    where = place_line(final, None, label="Places")
    if where:
        parts.append(where)
    if g.extras and g.kind == "roll":
        parts.append("\n".join(f"![[{x}|600]]" for x in g.extras))
    elif g.extras:
        parts.append(" ".join(f"![[{x}|300]]" for x in g.extras))
    if g.box_text:
        title = "Written on the box" if g.kind == "roll" else "Box text (machine-read, rough)"
        parts.append(callout("quote", title, g.box_text, "-" if g.kind == "reel" else ""))
    if g.sections_en or g.sections_fr:
        parts.append(bilingual(g.sections_en, g.sections_fr, "-"))
    if g.unlisted:
        parts.append(f"*{len(g.unlisted)} other images in the folder aren't in the README "
                     f"(e.g. {', '.join(g.unlisted[:3])}), so they have no notes.*")
    parts.append(f"## {item_kind.capitalize()}s\n\n" + cards_base(
        [f'file.inFolder("{g.folder}")', f'file.hasTag("{item_kind}")'], item_kind.capitalize() + "s",
        aspect=0.75 if g.kind == "roll" else 0.5625))
    write_note(note, props, "\n\n".join(parts), dry, keep_theme_tags_if_reviewed=False)
    return period


def make_thumb(g: Group, it: Item, dry: bool) -> str:
    rel = f"media/thumbs/{g.src.name}/{Path(it.file).stem}.jpg"
    out = VAULT / rel
    if out.exists():
        return rel
    stats["thumbnails"] += 1
    if dry:
        return rel
    out.parent.mkdir(parents=True, exist_ok=True)
    mid = max(0.0, (it.extra.get("duration") or 0) / 2)
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{mid:.2f}", "-i", str(g.src / it.file),
                        "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", "-y", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        warnings.append(f"{g.src.name}/{it.file}: no thumbnail ({r.stderr.strip()[:120]})")
        return it.media
    return rel


# ---------------------------------------------------------------- vault-wide pages

def link_media(groups: list[Group], dry: bool):
    for g in groups:
        sub = "rolls" if g.kind == "roll" else "films"
        link = VAULT / "media" / sub / g.src.name
        if link.is_symlink() and os.readlink(link) == str(g.src):
            continue
        stats["links"] += 1
        if not dry:
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.is_symlink():
                link.unlink()
            link.symlink_to(g.src, target_is_directory=True)
    for sub in ("rolls", "films"):
        for p in (VAULT / "media" / sub).glob("*") if (VAULT / "media" / sub).exists() else []:
            if p.is_symlink() and not p.exists():
                warnings.append(f"media/{sub}/{p.name} points to a folder that no longer exists")


def timeline(groups: list[Group], periods: dict, dry: bool):
    lines = ["# Timeline", "",
             "Slide rolls (📷) and Super 8 films (🎞) in date order. Generated by `tools/build_vault.py`: "
             "changes here are overwritten, so write in the roll notes instead.", ""]
    year = object()
    for g in sorted(groups, key=lambda g: g.sort()):
        if g.year != year:
            year = g.year
            lines += ["", f"## {year if year else 'Undated'}", ""]
        icon = "📷" if g.kind == "roll" else "🎞"
        q = f"{g.quarter} · " if g.quarter and g.quarter != "QX" else ""
        what = g.title_en or "*no README yet*"
        if g.kind == "reel":
            what = g.box_label or "Super 8"
        unit = "slides" if g.kind == "roll" else "clips"
        lines.append(f"- {icon} {q}[[{g.link}|{g.name}]]: {what} ({len(g.items)} {unit})")
    text = "\n".join(lines) + "\n"
    path = VAULT / "Timeline.md"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        stats["unchanged"] += 1
        return
    stats["updated" if path.exists() else "new"] += 1
    if not dry:
        path.write_text(text, encoding="utf-8")


def topic_pages(cfg: dict, used_periods: set, dry: bool):
    for p in cfg.get("periods", []):
        if p["name"] not in used_periods:
            continue
        tag = f"period/{slug(p['name'])}"
        create_once(VAULT / "Periods" / f"{p['name']}.md",
                    f"# {p['name']}\n\n*Write about this period here.*\n\n## Rolls and films\n\n"
                    + cards_base([f'file.hasTag("{tag}")', 'type == "roll" || type == "reel"'], "Rolls and films")
                    + "\n\n## Slides\n\n" + cards_base([f'file.hasTag("{tag}")', 'file.hasTag("slide")'], "Slides")
                    + "\n\n## Film clips\n\n" + cards_base([f'file.hasTag("{tag}")', 'file.hasTag("clip")'], "Clips", aspect=0.5625)
                    + f"\n\n{NOTES}\n\n", dry)
    for t in cfg.get("themes", []):
        tag = f"theme/{slug(t['name'])}"
        create_once(VAULT / "Themes" / f"{t['name']}.md",
                    f"# {t['name']}\n\n*Write about this theme here.* Slides are tagged `#{tag}` by keyword "
                    "(see `tools/papa.toml`); check them and set `themes_status: reviewed` once a slide's "
                    "themes are right.\n\n## Slides\n\n"
                    + cards_base([f'file.hasTag("{tag}")', 'file.hasTag("slide")'], "Slides",
                                 order=("file.name", "date"))
                    + "\n\n## Film clips\n\n"
                    + cards_base([f'file.hasTag("{tag}")', 'file.hasTag("clip")'], "Clips", aspect=0.5625,
                                 order=("file.name", "date"))
                    + f"\n\n{NOTES}\n\n", dry)


def place_index(groups: list[Group], gaz: Gazetteer) -> dict[str, dict[str, list[int]]]:
    """{country: {place: [sure, maybe]}} over the slides and clips of `groups`."""
    out: dict[str, dict[str, list[int]]] = defaultdict(dict)
    country_of = {name: country for name, country, is_c, _, _ in gaz.entries if not is_c}
    for g in groups:
        rp, rc, hd = *group_places(g, gaz), group_hedged(g, gaz)
        for it in g.items:
            sure, maybe, _, _ = place_info(*item_texts(it), gaz, rp, rc, hd)
            for p, i in [(p, 0) for p in sure] + [(p, 1) for p in maybe]:
                out[country_of.get(p, "")].setdefault(p, [0, 0])[i] += 1
    return out


def place_pages(index: dict, built: dict, dry: bool):
    lines = ["# Places", "",
             "Places named in the captions, box texts and roll titles, by country. Counts are slides "
             "and clips; *(?)* counts the ones where the caption isn't sure. Generated by "
             "`tools/build_vault.py` from `tools/places.toml`: changes here are overwritten.", ""]
    for country in sorted(index, key=lambda c: (c == "", c)):
        lines += [f"## {f'[[Places/{country}|{country}]]' if country else 'Other'}", ""]
        for p, (sure, maybe) in sorted(index[country].items()):
            lines.append(f"- [[Places/{p}|{p}]]: {sure}" + (f" + {maybe} (?)" if maybe else ""))
        lines.append("")
    text = "\n".join(lines)
    path = VAULT / "Places.md"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        stats["updated" if path.exists() else "new"] += 1
        if not dry:
            path.write_text(text, encoding="utf-8")

    def page(name: str, country: str | None):
        tag = f"place/{slug(name)}"
        head = f"# {name}\n\n" + (f"In [[Places/{country}|{country}]]. " if country else "")
        create_once(VAULT / "Places" / f"{name}.md",
                    head + "*Write about this place here.* Slides and clips that name it, "
                    "including the uncertain ones (see each slide's `places_maybe`).\n\n## Slides\n\n"
                    + cards_base([f'file.hasTag("{tag}")', 'file.hasTag("slide")'], "Slides")
                    + "\n\n## Film clips\n\n"
                    + cards_base([f'file.hasTag("{tag}")', 'file.hasTag("clip")'], "Clips", aspect=0.5625)
                    + f"\n\n{NOTES}\n\n", dry)

    for country, places in built.items():
        if country:
            page(country, None)
        for p in places:
            page(p, country or None)


CSS = {
    "papa": """/* Papa slides: English and French captions. Generated by tools/build_vault.py. */
.callout[data-callout="en"] { --callout-color: 52, 120, 190; --callout-icon: lucide-languages; }
.callout[data-callout="fr"] { --callout-color: 190, 60, 70; --callout-icon: lucide-languages; }
.callout[data-callout="en"] .callout-title::after { content: " · EN"; opacity: .6; }
.callout[data-callout="fr"] .callout-title::after { content: " · FR"; opacity: .6; }
""",
    "papa-hide-fr": """/* Turn on to show only English. Generated by tools/build_vault.py. */
.callout[data-callout="fr"] { display: none; }
""",
    "papa-hide-en": """/* Turn on to show only French. Generated by tools/build_vault.py. */
.callout[data-callout="en"] { display: none; }
""",
}

HOME = """# Papa's slides

Slides from Dad's rolls (1951–1971) and clips from his Super 8 films, with the
descriptions from the READMEs in `~/Pictures/Papa`.

- [[Timeline]]: every roll and film in date order
- **Periods**: [[Periods/Afghanistan 1951–52]] · [[Periods/Rome and Paris 1952]] · [[Periods/Iran 1955–65]] · [[Periods/Later years]]
- [[Places]]: every place named in the captions, by country
- **Themes**: [[Themes/Road trips]] · [[Themes/Mountains]] · [[Themes/Markets]] · [[Themes/Locals]] · [[Themes/Sheep herders]]

## Languages

Captions come in a blue **English** box and a red **Français** box. To show only
one language: *Settings → Appearance → CSS snippets*, turn on `papa-hide-fr`
(English only) or `papa-hide-en` (French only).

## Updating

The READMEs are the source of truth. After changing a README, adding slides or
adding a roll in `~/Pictures/Papa`, run:

    python3 tools/build_vault.py --dry-run   # see what would change
    python3 tools/build_vault.py

What you write under **Notes** in any note is kept, and so are your own
properties and tags. Theme tags are keyword guesses until you set
`themes_status: reviewed` on a slide; after that the script leaves them alone.

## Notes

"""


def obsidian_config(dry: bool):
    snippets = VAULT / ".obsidian" / "snippets"
    for name, css in CSS.items():
        p = snippets / f"{name}.css"
        if not p.exists() or p.read_text() != css:
            stats["config"] += 1
            if not dry:
                snippets.mkdir(parents=True, exist_ok=True)
                p.write_text(css)
    appearance = VAULT / ".obsidian" / "appearance.json"
    if not appearance.exists() and not dry:
        appearance.write_text(json.dumps({"enabledCssSnippets": ["papa"]}, indent=2))
    create_once(VAULT / "Home.md", HOME, dry)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    ap.add_argument("--only", help="only rolls/reels whose folder name matches this regex")
    ap.add_argument("--no-thumbs", action="store_true", help="don't make clip thumbnails")
    args = ap.parse_args()
    cfg = tomllib.loads((VAULT / "tools" / "papa.toml").read_text(encoding="utf-8"))
    src = Path(os.path.expanduser(cfg["source"]))
    skip = set(cfg.get("skip", []))

    groups = [load_roll(d, cfg) for d in sorted(src.iterdir())
              if d.is_dir() and d.name.startswith("Papa_-_") and d.name not in skip]
    if "Super8_clips" not in skip:
        groups += load_reels(src / "Super8_clips")
    all_groups = groups
    if args.only:
        groups = [g for g in groups if re.search(args.only, g.src.name, re.I)]

    themes = compile_themes(cfg)
    gaz = Gazetteer.load(VAULT / "tools" / "places.toml")
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    new_state = dict(state)
    link_media(groups, args.dry_run)
    used_periods = set()
    for g in groups:
        p = build_group(g, cfg, themes, gaz, state, new_state, args.dry_run, not args.no_thumbs)
        if p:
            used_periods.add(p)
    used_periods |= {period_of(g, cfg) for g in all_groups} - {None}
    timeline(all_groups, {}, args.dry_run)
    topic_pages(cfg, used_periods, args.dry_run)
    index = place_index(all_groups, gaz)
    place_pages(index, place_index(groups, gaz), args.dry_run)
    obsidian_config(args.dry_run)
    if not args.dry_run and new_state != state:
        STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    rolls = sum(g.kind == "roll" for g in groups)
    reels = len(groups) - rolls
    items = sum(len(g.items) for g in groups)
    print(f"{'Would change' if args.dry_run else 'Done'}: {rolls} rolls, {reels} films, {items} slides and clips")
    print("  " + ", ".join(f"{v} {k}" for k, v in sorted(stats.items())) if stats else "  nothing to do")
    theme_counts = Counter()
    for g in groups:
        for it in g.items:
            theme_counts.update(themes_for(*item_texts(it), themes))
    if theme_counts:
        print("  themes (keyword guesses): " + ", ".join(f"{k} {v}" for k, v in theme_counts.most_common()))
    found = place_index(groups, gaz)
    named = sum(1 for g in groups for it in g.items
                if any(place_info(*item_texts(it), gaz, *group_places(g, gaz))[:2]))
    print(f"  places: {named} of {items} slides and clips have one; "
          f"{sum(len(v) for v in found.values())} different places")
    shown = {g.src.name for g in groups}
    for w in dict.fromkeys(warnings):
        if w.split(":")[0] in shown or w.startswith("media/"):
            print(f"  ! {w}")


if __name__ == "__main__":
    sys.exit(main())
