# Rules for agents working in this vault

This vault holds Marco's technical notes: mathematics, physics, electrical engineering
and machine learning. Some notes are transcribed from scanned notebooks and course
notes; others are written directly. These rules apply to any agent (Claude, Gemma or
another model).

Journal entries, even ones about technical work (speaker wiring, antennas, circuits
for an art piece), belong in `../personal_history`. This vault is for the notes
themselves: derivations, lecture notes, problem sets, references.

## Never

- Never change, rename or delete an existing note, page image or PDF unless Marco asks.
  New material goes to a staging folder first (see the workflow below).
- Never translate. French stays French and English stays English, titles included.
- Never reword or "improve" what is on the page, and never correct its maths. A
  mistake in a derivation stays as written; point it out in the callout.
- Never guess a date, course or teacher and present it as fact.

## The scans

- Scans are saved as `attachments/scan_journal_<name>.pdf` (the `scan_journal_` prefix
  is what `tools/scan_index.py` looks for). Page images are
  `attachments/pages/scan_<name>_pNNN.jpg`, where NNN is the page's position in the PDF.
- The first scan is `attachments/scan_journal_phys_ee_1998.pdf` (name `scan_phys_ee_1998`,
  32 pages), copied from `../raw_dumps/scan_phys_ee_1998.pdf`.

## Workflow

The tools are copies of the ones in `../personal_history/tools/`, and they work on this
vault (each finds its vault from its own location). Run `journal_scan.py` with
`~/Projects/gemma-photo-pipeline/.venv/bin/python`; it needs `Pillow`.

Follow the workflow in `../personal_history/AGENTS.md` ("Workflow", steps 1–10), with
these differences:

- **Orientation:** set it by hand with `--set` after looking at the contact sheet. Gemma
  is not reliable at it.
- **One note per topic, not per entry.** A topic is one subject treated on the page or
  run of pages: a derivation, a lecture, a problem, a circuit. A topic that runs over
  several pages is one note; a page with two topics is cropped, as in personal_history.
- **After approval,** move the notes to the vault root, save `orient.json` and
  `crops.json` to `tools/settings/` as `<name>_orient.json` and `<name>_crops.json`,
  delete the staging folder and run `python3 tools/scan_index.py`.

## Transcription

The conventions in `../personal_history/AGENTS.md` apply (crossed-out words, `[?]`,
margins in `` `[…]` ``, `<u>underline</u>`, editor's additions in `` `[…]` ``). In addition:

- **Maths:** write equations in LaTeX, `$…$` inline and `$$…$$` for a displayed line,
  keeping the page's own symbols, order of steps and notation (even when unusual).
  One displayed equation per line of the page.
- **Long calculations:** transcribe every step that is written. Don't fill in steps the
  page skips.
- **Diagrams:** describe them in `` `[diagram: …]` `` where they are: what is drawn, the
  labels quoted, the values on components and axes. Example:
  `` `[diagram: a voltage divider, R1 "10k" over R2 "4.7k", output "Vout" taken across R2]` ``.
- **Units and values** are copied as written.

## Notes

### File name

`YYYY-MM-DD_Title-In-Title-Case.md`, or `YYYY_pNNN_Title.md` when the page has no date
(the year and the first scan page). Hyphens for spaces, ASCII only, no `:?/'`.

### Frontmatter

```yaml
---
date: 1998                  # YYYY-MM-DD only when written on the page; else the year
dated: estimated            # only when the date is inferred
field: ["[[Physics]]", "[[Electrical Engineering]]"]
topics: [electromagnetism, maxwell-equations]
type: notebook              # notebook, lecture-notes, problem-set, derivation, reference, project
course:                     # only when the page names it
source: scan_phys_ee_1998   # the notebook, book or course the note comes from
scan: scan_phys_ee_1998_p004   # the PDF page(s); a list when several. None for notes written directly
---
```

- **`field`:** one or more of the pages in `Fields/`: Mathematics, Physics, Electrical
  Engineering, Machine Learning. Write them as quoted links, as above, so the note
  appears on the field's page. Ask before adding a field; a new one needs a page in
  `Fields/` (copy an existing one).
- **`topics`:** two to five lower-case, hyphenated labels (`fourier-series`,
  `rc-circuits`, `gradient-descent`). Reuse existing ones first:
  `grep -h '^topics:' *.md | tr -d '[]' | sed 's/topics: //' | tr ',' '\n' | sed 's/^ *//' | sort | uniq -c | sort -rn`
- **`source`:** what the note was copied from, so all the notes from one notebook or
  course can be listed together.

### Body

```markdown
# Title of the Topic

<the transcription>

> [!note] Transcription notes
> Uncertain readings, identifications (a theorem's usual name, the textbook a
> problem comes from), mistakes in the maths, links to related notes.

---

## Original Page
![[attachments/pages/scan_phys_ee_1998_p004.jpg]]
```

- The title names the topic, in the page's language.
- Use `## Original Pages` when there are several images, in page order. Shared pages
  are cropped, with the "Part of" line under each crop, as in personal_history.

## Navigation

- `Fields/` pages hold a Bases table of the notes that link to them. They are written
  by hand and need no regenerating.
- `Home.md` lists every note that has a `field`.
- `Scan index.md` is generated by `python3 tools/scan_index.py`.

## Hand-off

As in personal_history: the number of notes, the shared (cropped) pages, pages with no
note, pages to rescan, uncertain readings, new topic labels, and any clue to a date or
course.
