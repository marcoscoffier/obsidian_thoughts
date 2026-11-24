#!/usr/bin/env python3
"""Name and describe the slides of a roll that has no README yet, with the local
Gemma model (vLLM), then rename the files and write README.md / README_fr.md in
the same format as the other rolls.

Two steps, so the descriptions can be read before anything is renamed:

    describe_roll.py describe <roll dir> --title "..." --box "text on the box"
        -> writes <roll dir>/describe_plan.json (resumable: done slides are kept)
    describe_roll.py apply <roll dir>
        -> renames Papa_X_<n>.jpg to NN_<name>.jpg and writes both READMEs

The old names are kept in the READMEs ("formerly ..."), so nothing is lost.
Needs: openai, Pillow (e.g. ~/Projects/gemma-photo-pipeline/.venv/bin/python).
"""

import argparse
import base64
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

from openai import OpenAI
from PIL import Image

EXAMPLES = """Examples of the style wanted (from other rolls; copy the style, not the words):

name: rue_bazar_charrette_passants
en: A shopping street in Rasht (?): passers-by in suits and jackets, a handcart, shops with wooden eaves.
fr: Rue commerçante de Rasht (?) : passants en costume ou en veste, une charrette à bras, boutiques aux auvents de bois.

name: salle_controle_pupitre_hommes
en: Inside the control room: a grey console with dials and knobs, a cabinet of transmitter racks behind, men standing and sitting on wooden stools reading papers, sun coming through the window.
fr: Dans la salle de contrôle : un pupitre gris avec cadrans et boutons, une armoire d'émetteurs derrière, des hommes debout ou assis sur des tabourets de bois lisant des papiers, le soleil entre par la fenêtre.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "en": {"type": "string"},
        "fr": {"type": "string"},
    },
    "required": ["name", "en", "fr"],
}


def natural(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def slides(roll: Path) -> list[Path]:
    """The scans to describe: Papa_*_<n>.jpg in number order (not box photos)."""
    files = [p for p in roll.iterdir() if p.suffix.lower() in {".jpg", ".jpeg"}
             and not re.match(r"(box|IMG_)", p.name, re.I) and not re.match(r"\d\d_", p.name)]
    return sorted(files, key=lambda p: natural(p.name))


def image_url(path: Path, edge: int = 1024) -> tuple[str, bool]:
    im = Image.open(path).convert("RGB")
    vertical = im.height > im.width * 1.1
    im.thumbnail((edge, edge))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), vertical


def slug(text: str, words: int = 6) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    parts = [w for w in re.split(r"[^a-z0-9]+", text) if w][:words]
    return "_".join(parts) or "diapositive"


def describe(args):
    roll = args.roll.expanduser().resolve()
    plan_path = roll / "describe_plan.json"
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else {}
    plan.setdefault("title", args.title)
    plan.setdefault("box", args.box)
    plan.setdefault("slides", {})
    client = OpenAI(base_url=args.base_url, api_key="none")
    model = args.model or client.models.list().data[0].id
    files = slides(roll)
    print(f"{roll.name}: {len(files)} slides, model {model}", flush=True)
    previous = []
    for i, f in enumerate(files, 1):
        if f.name in plan["slides"]:
            previous.append(plan["slides"][f.name]["en"])
            continue
        url, vertical = image_url(f)
        context = (f"This is slide {i} of {len(files)} from a box of colour slides taken by my father.\n"
                   f"Roll: {plan['title']}\nWritten on the box: {plan['box']}\n")
        if previous:
            context += "The two slides before this one were described as:\n" + "\n".join(
                f"- {p}" for p in previous[-2:]) + "\n"
        prompt = (context + "\n" + EXAMPLES + """
Describe this slide the same way. Rules:
- Describe only what is visible: the subject first, then the setting and details (people, clothes, vehicles, buildings, landscape, light).
- One or two sentences, plain and concrete, no praise or mood words.
- You may suggest a place from the box text when the image fits it, always followed by "(?)". Never state a place as certain.
- If it is clearly the same scene as the slide before, say so ("The same ...").
- Don't comment on colour casts, fading or the film stock.
- Don't start every description the same way; vary it as the examples do, and don't repeat the place name if the slide before already gave it.
- name: 3 to 6 French words naming what is distinctive in this slide (e.g. "dome_rocher_oliviers_murets", "avion_passerelle_tarmac"), lower case, no accents, separated by underscores. Avoid vague words like paysage, vue, photo, image.
- en: the English description. fr: the same description in natural French (French punctuation: a space before ":" and "?").
Answer with JSON only.""")
        try:
            r = client.chat.completions.create(
                model=model, temperature=0.2, max_tokens=700,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": url}},
                    {"type": "text", "text": prompt}]}],
                response_format={"type": "json_schema", "json_schema": {"name": "slide", "schema": SCHEMA}},
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            d = json.loads(r.choices[0].message.content)
        except Exception as e:      # keep going; the slide is retried on the next run
            print(f"  {f.name}: failed ({e})", flush=True)
            continue
        entry = {"name": slug(d["name"]), "en": d["en"].strip(), "fr": d["fr"].strip(), "vertical": vertical}
        if vertical:
            entry["en"] = entry["en"].rstrip(".") + " (vertical slide)."
            entry["fr"] = entry["fr"].rstrip(".") + " (diapositive verticale)."
        plan["slides"][f.name] = entry
        previous.append(entry["en"])
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
        print(f"  {i:02d} {f.name} -> {entry['name']}", flush=True)
    done = sum(f.name in plan["slides"] for f in files)
    print(f"{roll.name}: {done} of {len(files)} described -> {plan_path}")
    return 0 if done == len(files) else 1


def apply(args):
    roll = args.roll.expanduser().resolve()
    plan = json.loads((roll / "describe_plan.json").read_text())
    files = slides(roll)
    missing = [f.name for f in files if f.name not in plan["slides"]]
    if missing:
        sys.exit(f"Not described yet: {', '.join(missing)}")
    if (roll / "README.md").exists() and not args.force:
        sys.exit(f"{roll / 'README.md'} exists; use --force to overwrite it")
    width = max(2, len(str(len(files))))
    renames, used = [], set()
    for i, f in enumerate(files, 1):
        base = f"{i:0{width}d}_{plan['slides'][f.name]['name']}"
        new = f"{base}{f.suffix.lower()}"
        n = 2
        while new in used:
            new, n = f"{base}_{n}{f.suffix.lower()}", n + 1
        used.add(new)
        renames.append((f, roll / new))
    for old, new in renames:
        if new.exists():
            sys.exit(f"{new.name} already exists; nothing renamed")

    old_pattern = re.sub(r"\d+(\.\w+)$", r"<n>\1", files[0].name)
    n = len(files)
    title, box = plan["title"], plan["box"]
    title_fr = plan.get("title_fr") or title
    en = [f"# Dad – {title}", "",
          f"Descriptions of {n} slides, written by a local vision model (Gemma 4) from the images and "
          "from what is written on the box; not yet reviewed.",
          'Place identifications are hypotheses, marked "?" where uncertain.', "",
          "## What is written on the box", "", box, "",
          "## Order and proposed names", "",
          f"The files have been renamed `NN_<name>.jpg`. They used to be called `{old_pattern}`. "
          f"The original order is kept: the new numbers run from 01 to {n:02d}.",
          "(Version française : README_fr.md)", "",
          "## Photos (proposed name, then description)", ""]
    fr = [f"# Papa – {title_fr}", "",
          f"Description de {n} diapositives faite par un modèle de vision local (Gemma 4) à partir des "
          "images et de ce qui est écrit sur la boîte ; pas encore relue.",
          "Les identifications de lieux sont des hypothèses, marquées « ? » quand elles sont incertaines.", "",
          "## Ce qui est écrit sur la boîte", "", box, "",
          "## Ordre et noms proposés", "",
          f"Les fichiers ont été renommés `NN_<nom>.jpg`. Ils s'appelaient avant `{old_pattern}`. "
          f"L'ordre d'origine est conservé : les nouveaux numéros vont de 01 à {n:02d}.",
          "(English version: README.md)", "",
          "## Photos (nom proposé, ancien nom, description)", ""]
    for old, new in renames:
        s = plan["slides"][old.name]
        en += [f"**{new.name}** (formerly `{old.name}`) : {s['en']}", ""]
        fr += [f"**{new.name}** (ancien nom : `{old.name}`) : {s['fr']}", ""]
    if args.dry_run:
        for old, new in renames:
            print(f"{old.name} -> {new.name}")
        return 0
    for old, new in renames:
        old.rename(new)
    (roll / "README.md").write_text("\n".join(en).rstrip() + "\n", encoding="utf-8")
    (roll / "README_fr.md").write_text("\n".join(fr).rstrip() + "\n", encoding="utf-8")
    print(f"{roll.name}: renamed {len(renames)} files, wrote README.md and README_fr.md")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("describe")
    d.add_argument("roll", type=Path)
    d.add_argument("--title", required=True, help='e.g. "1962 Q1 – Jerusalem (23 March 1962)"')
    d.add_argument("--box", default="", help="what is written on the box")
    d.add_argument("--base-url", default="http://localhost:8000/v1")
    d.add_argument("--model", default=None, help="default: the first model the server lists")
    a = sub.add_parser("apply")
    a.add_argument("roll", type=Path)
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--force", action="store_true")
    args = ap.parse_args()
    return describe(args) if args.cmd == "describe" else apply(args)


if __name__ == "__main__":
    sys.exit(main())
