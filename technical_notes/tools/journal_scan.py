#!/usr/bin/env python3
"""Turn a Genius Scan PDF of a notebook into upright page images and draft
transcriptions, with the local Gemma model (vLLM on localhost:8000).

Everything is written to a work folder (default: _import_<name>/ in the vault),
so nothing in the vault itself changes until the notes are reviewed.

    journal_scan.py extract attachments/scan_journal_1997.pdf --name scan_1997
        -> _import_scan_1997/raw/scan_1997_p001.jpg ... (original JPEGs, not recompressed)
    journal_scan.py orient scan_1997 [--set 8=90 --set 9=270]
        -> Gemma picks the upright rotation of each page; orient.json; pages/ (upright)
           and contact.jpg to check. --set fixes a page by hand (degrees counter-clockwise).
    journal_scan.py views scan_1997
        -> views/NNN_full.jpg, NNN_top.jpg, NNN_bot.jpg: each upright page whole (for
           the layout) and as two overlapping halves at full resolution (for reading)
    journal_scan.py crop scan_1997
        -> cuts the parts listed in crops.json out of the upright pages, as
           pages/scan_1997_p007_part1.jpg ..., for notes that share a page
    journal_scan.py check scan_1997
        -> checks the drafted notes: every page used, every crop used once and
           followed by its "Part of" line, every image and note link resolves
    journal_scan.py transcribe scan_1997 [--pages 3,14,33] [--mode whole|halves|both]
        -> transcripts.json (resumable: pages already done are kept unless --redo)

Needs: openai, Pillow (e.g. ~/Projects/gemma-photo-pipeline/.venv/bin/python).
"""

import argparse
import base64
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

VAULT = Path(__file__).resolve().parent.parent


def work_dir(name: str) -> Path:
    return VAULT / f"_import_{name}"


def client_model(base_url: str, model: str | None):
    from openai import OpenAI
    c = OpenAI(base_url=base_url, api_key="none")
    return c, model or c.models.list().data[0].id


def data_url(im: Image.Image, edge: int, quality: int = 90) -> str:
    im = im.convert("RGB")
    im.thumbnail((edge, edge))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


LATEX = {"rightarrow": "→", "leftarrow": "←", "uparrow": "↑", "downarrow": "↓",
         "Rightarrow": "⇒", "Leftarrow": "⇐", "leftrightarrow": "↔"}


def clean(text: str) -> str:
    """Gemma sometimes writes arrows as LaTeX ($\\rightarrow$, and in JSON the \\r
    can arrive as a carriage return): turn them into the Unicode arrows."""
    text = text.replace("\r", "\\r")
    text = re.sub(r"\$?\\(r?ightarrow|[A-Za-z]+arrow)\$?", lambda m: LATEX.get(
        "rightarrow" if m.group(1) in ("ightarrow", "rightarrow") else m.group(1), m.group(0)), text)
    return text


def ask(client, model, images: list[str], prompt: str, schema: dict, max_tokens: int):
    content = [{"type": "image_url", "image_url": {"url": u}} for u in images]
    content.append({"type": "text", "text": prompt})
    r = client.chat.completions.create(
        model=model, temperature=0, max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_schema", "json_schema": {"name": "out", "schema": schema}},
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    d = json.loads(r.choices[0].message.content)
    if isinstance(d.get("text"), str):
        d["text"] = clean(d["text"])
    return d


def font(size: int):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


# ---------------------------------------------------------------- extract

def extract(args):
    pdf = args.pdf.expanduser().resolve()
    out = work_dir(args.name) / "raw"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdfimages", "-j", str(pdf), f"{tmp}/p"], check=True)
        files = sorted(Path(tmp).glob("p-*"))
        for i, f in enumerate(files, 1):
            dest = out / f"{args.name}_p{i:03d}{f.suffix.lower()}"
            dest.write_bytes(f.read_bytes())
    (work_dir(args.name) / "source.txt").write_text(str(pdf) + "\n")
    print(f"{len(files)} pages -> {out}")


# ---------------------------------------------------------------- orient

ORIENT_SCHEMA = {
    "type": "object",
    "properties": {"upright": {"type": "integer", "enum": [1, 2, 3, 4]},
                   "reason": {"type": "string"}},
    "required": ["upright", "reason"],
}
ANGLES = [0, 90, 180, 270]          # counter-clockwise, as PIL's rotate()


def rotation_grid(im: Image.Image, cell: int = 640) -> Image.Image:
    grid = Image.new("RGB", (cell * 2, cell * 2 + 0), "white")
    d = ImageDraw.Draw(grid)
    for k, a in enumerate(ANGLES):
        r = im.rotate(a, expand=True)
        r.thumbnail((cell - 20, cell - 60))
        x, y = (k % 2) * cell, (k // 2) * cell
        grid.paste(r, (x + 10, y + 50))
        d.rectangle([x + 10, y + 5, x + 60, y + 45], fill="red")
        d.text((x + 24, y + 6), str(k + 1), fill="white", font=font(34))
    return grid


def orient(args):
    wd = work_dir(args.name)
    raw = sorted((wd / "raw").glob("*.jpg"))
    path = wd / "orient.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    manual = {}
    for s in args.set or []:
        p, a = s.split("=")
        manual[f"{args.name}_p{int(p):03d}.jpg"] = int(a) % 360
    client = model = None
    for f in raw:
        if f.name in manual:
            data[f.name] = {"angle": manual[f.name], "by": "hand"}
            continue
        if f.name in data and not args.redo:
            continue
        if client is None:
            client, model = client_model(args.base_url, args.model)
        grid = rotation_grid(ImageOps.exif_transpose(Image.open(f)))
        prompt = ("This picture shows the same handwritten notebook page four times, rotated "
                  "differently, numbered 1 to 4 in red. In which one is the handwriting upright, "
                  "so the lines of text run left to right and can be read normally? If the page "
                  "has writing in more than one direction, choose the one where most of the "
                  "writing is upright. Answer with JSON.")
        try:
            d = ask(client, model, [data_url(grid, 1280)], prompt, ORIENT_SCHEMA, 200)
        except Exception as e:
            print(f"  {f.name}: failed ({e})", flush=True)
            continue
        data[f.name] = {"angle": ANGLES[d["upright"] - 1], "by": "gemma", "reason": d["reason"]}
        print(f"  {f.name}: {data[f.name]['angle']}°  {d['reason'][:80]}", flush=True)
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))

    pages = wd / "pages"
    pages.mkdir(exist_ok=True)
    thumbs = []
    for f in raw:
        if f.name not in data:
            continue
        a = data[f.name]["angle"]
        dest = pages / f.name
        if a == 0:
            dest.write_bytes(f.read_bytes())
        else:
            Image.open(f).rotate(a, expand=True).save(dest, "JPEG", quality=95)
        t = Image.open(dest)
        t.thumbnail((320, 320))
        thumbs.append((f.name, a, data[f.name]["by"], t))
    cols, W = 6, 330
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W, rows * (W + 24)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (n, a, by, t) in enumerate(thumbs):
        x, y = (i % cols) * W, (i // cols) * (W + 24)
        sheet.paste(t, (x, y + 24))
        num = re.search(r"_p(\d+)", n).group(1)
        d.text((x + 4, y + 2), f"p{num}  {a}° {'(hand)' if by == 'hand' else ''}", fill="red", font=font(18))
    sheet.save(wd / "contact.jpg", quality=85)
    print(f"{len(thumbs)} upright pages -> {pages}; contact sheet -> {wd / 'contact.jpg'}")


# ---------------------------------------------------------------- transcribe

TRANSCRIBE_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "languages": {"type": "array", "items": {"type": "string"}},
        "dates": {"type": "array", "items": {"type": "string"}},
        "names": {"type": "array", "items": {"type": "string"}},
        "drawings": {"type": "string"},
    },
    "required": ["text", "languages", "dates", "names", "drawings"],
}

RULES = """Rules:
- Copy the handwriting exactly, line by line, in the language it is written in. The notebook mixes French and English: never translate, never correct spelling or grammar, keep abbreviations (w/, &, ex., cf.) and accents as written.
- Write arrows as the characters →, ←, ↑, ↓ (never LaTeX like $\\rightarrow$). Keep list structure: one item per line, with "-" or "→" as written.
- Words crossed out: ~~word~~. A word you cannot read: [?]. A word you are unsure of: word[?].
- Writing in a margin, at an angle or sideways: put it where it belongs, as `[left margin: ...]`, `[right margin, sideways: ...]`, `[top, upside down: ...]`.
- Drawings and diagrams: in the text, a short `[sketch: what it shows]` where the drawing is; labels written on a drawing go inside it: `[sketch: a cylinder, labelled "lumière"]`.
- Do not add a title, comments or a summary to the text.
- dates: any dates written on the page, as written. names: people, artists, writers and places named on the page. drawings: one or two sentences on what the drawings show, or "" if there are none.
Answer with JSON only."""


def transcribe(args):
    wd = work_dir(args.name)
    files = sorted((wd / "pages").glob("*.jpg"))
    if args.pages:
        want = {int(p) for p in args.pages.split(",")}
        files = [f for f in files if int(re.search(r"_p(\d+)", f.name).group(1)) in want]
    out = wd / (args.out or "transcripts.json")
    data = json.loads(out.read_text()) if out.exists() else {}
    client, model = client_model(args.base_url, args.model)
    print(f"{len(files)} pages, model {model}, mode {args.mode}", flush=True)
    for f in files:
        key = f.name
        if key in data and data[key].get(args.mode) and not args.redo:
            continue
        im = Image.open(f).convert("RGB")
        intro = (f"This is a page of my handwritten notebook from 1997, when I was an art student "
                 f"at the Beaux-Arts in Paris (notes in French and English, plans for installations, "
                 f"sketches). Transcribe it.\n")
        entry = data.setdefault(key, {})
        try:
            if args.mode in ("whole", "both"):
                entry["whole"] = ask(client, model, [data_url(im, args.edge)], intro + RULES,
                                     TRANSCRIBE_SCHEMA, 4000)
            if args.mode in ("halves", "both"):
                # The server takes one image per request: read the top and bottom halves
                # separately (they overlap by 10% so no line is cut in two).
                w, h = im.size
                parts = []
                for label, box in (("top", (0, 0, w, int(h * 0.55))), ("bottom", (0, int(h * 0.45), w, h))):
                    prompt = (intro + f"This image is only the {label} half of the page, so the "
                              f"{'last' if label == 'top' else 'first'} lines may be cut off: copy only "
                              "lines you can see whole.\n" + RULES)
                    parts.append(ask(client, model, [data_url(im.crop(box), args.edge)], prompt,
                                     TRANSCRIBE_SCHEMA, 3000))
                entry["halves"] = {
                    "text": parts[0]["text"].rstrip() + "\n\n[--- bottom half (overlaps the top by a few lines) ---]\n\n"
                            + parts[1]["text"].lstrip(),
                    **{k: sorted(set(parts[0][k]) | set(parts[1][k])) for k in ("languages", "dates", "names")},
                    "drawings": " ".join(p["drawings"] for p in parts if p["drawings"]),
                }
        except Exception as e:
            print(f"  {key}: failed ({e})", flush=True)
            continue
        out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
        print(f"  {key}: done", flush=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"-> {out}")


def views(args):
    wd = work_dir(args.name)
    out = wd / "views"
    out.mkdir(exist_ok=True)
    pages = [f for f in sorted((wd / "pages").glob("*.jpg")) if "_part" not in f.name]
    for f in pages:
        im = Image.open(f)
        w, h = im.size
        n = re.search(r"_p(\d+)", f.name).group(1)
        a = im.copy()
        a.thumbnail((1500, 1500))
        a.save(out / f"{n}_full.jpg", quality=88)
        for label, box in (("top", (0, 0, w, int(h * .55))), ("bot", (0, int(h * .45), w, h))):
            c = im.crop(box)
            c.thumbnail((1600, 1600))
            c.save(out / f"{n}_{label}.jpg", quality=90)
    print(f"{len(pages)} pages -> {out}")


def check(args):
    wd = work_dir(args.name)
    notes = sorted((wd / "notes").glob("*.md"))
    names = {n.stem for n in notes}
    pages = [f.name for f in sorted((wd / "pages").glob("*.jpg")) if "_part" not in f.name]
    parts = [f.name for f in sorted((wd / "pages").glob("*_part*.jpg"))]
    attach = VAULT / "attachments" / "pages"
    used, problems = {}, []
    for n in notes:
        text = n.read_text()
        if not text.startswith("---\n") or "\ndate:" not in text.split("\n---\n")[0]:
            problems.append(f"{n.name}: frontmatter missing or has no date")
        lines = text.splitlines()
        for i, line in enumerate(lines):
            for img in re.findall(r"!\[\[attachments/pages/([^\]|]+)\]\]", line):
                used.setdefault(img, []).append(n.name)
                if not (attach / img).exists():
                    problems.append(f"{n.name}: {img} is not in attachments/pages/")
                if "_part" in img and not (i + 1 < len(lines) and lines[i + 1].startswith("*Part of [[")):
                    problems.append(f"{n.name}: {img} has no 'Part of' line after it")
        for link in re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]", text):
            if not link.startswith("attachments/") and link not in names and not (VAULT / f"{link}.md").exists():
                problems.append(f"{n.name}: link [[{link}]] goes nowhere")
    for pg in pages:
        stem = pg[:-4]
        whole = pg in used
        cut = [x for x in parts if x.startswith(stem + "_part")]
        if not whole and not cut:
            problems.append(f"{pg}: not shown in any note")
        if whole and cut:
            problems.append(f"{pg}: shown whole and as crops (pick one)")
        for x in cut:
            if len(used.get(x, [])) != 1:
                problems.append(f"{x}: used in {len(used.get(x, []))} notes (should be 1)")
    print(f"{len(notes)} notes, {len(pages)} pages, {len(parts)} crops")
    print("\n".join(problems) if problems else "all good")
    return 1 if problems else 0


def crop(args):
    """crops.json: {"7": [[0, 0.57], [0.55, 1]], "21": [[0, 0.15], ...]} gives, for each
    page, the parts in order as [top, bottom] fractions of the page height, or
    [top, bottom, left, right] to cut a column too."""
    wd = work_dir(args.name)
    spec = json.loads((wd / "crops.json").read_text())
    for page, parts in spec.items():
        src = wd / "pages" / f"{args.name}_p{int(page):03d}.jpg"
        im = Image.open(src)
        w, h = im.size
        for k, part in enumerate(parts, 1):
            top, bottom, left, right = (part + [0, 1])[:4]
            out = src.with_name(f"{src.stem}_part{k}.jpg")
            im.crop((int(left * w), int(top * h), int(right * w), int(bottom * h))).save(out, "JPEG", quality=92)
            print(out.name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--model", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("pdf", type=Path)
    e.add_argument("--name", required=True, help="e.g. scan_1997 (page files become scan_1997_p001.jpg)")
    o = sub.add_parser("orient")
    o.add_argument("name")
    o.add_argument("--set", action="append", help="PAGE=DEGREES (counter-clockwise), e.g. 8=90")
    o.add_argument("--redo", action="store_true")
    c = sub.add_parser("crop")
    c.add_argument("name")
    v = sub.add_parser("views")
    v.add_argument("name")
    k = sub.add_parser("check")
    k.add_argument("name")
    t = sub.add_parser("transcribe")
    t.add_argument("name")
    t.add_argument("--pages", help="e.g. 3,14,33")
    t.add_argument("--mode", choices=["whole", "halves", "both"], default="halves",
                   help="halves reads better: on the 1997 test the whole page missed a column")
    t.add_argument("--edge", type=int, default=1536, help="longest side of each image sent")
    t.add_argument("--out", help="default transcripts.json")
    t.add_argument("--redo", action="store_true")
    args = ap.parse_args()
    return {"extract": extract, "orient": orient, "views": views, "crop": crop, "check": check,
            "transcribe": transcribe}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
