# Rules for agents working in this vault

This vault holds Marco's personal history: notebook pages transcribed into notes, plus
recent therapy notes. These rules cover turning a scanned notebook into notes. They
apply to any agent (Claude, Gemma or another model).

## Never

- Never change, rename or delete an existing note, page image or PDF unless Marco asks.
  New material goes to a staging folder first (see the workflow below).
- Never translate. French stays French and English stays English. This applies to
  titles too, when the entry is in French.
- Never reword, summarise, tidy up or "improve" the writing. A note's body is what is
  on the page. Spelling slips, abbreviations and odd punctuation stay as written.
- Never guess a date and present it as fact. Never present a guessed name or place as
  certain.
- Never edit `life_timeline.canvas` unless asked.

## The scans

- Genius Scan crops and straightens each page. Scan in colour or grayscale, not black
  and white: thresholding loses pencil and faint ink.
- Scans are saved as `attachments/scan_journal_<year>[_n].pdf`. Page images are named
  `attachments/pages/scan_<year>[_n]_pNNN.jpg`, where NNN is the page's position in the
  PDF (001, 002, …).

## Workflow

The tool is `tools/journal_scan.py`. Run it with a Python that has `openai` and
`Pillow` (`~/Projects/gemma-photo-pipeline/.venv/bin/python`); the commands below are
written as `journal_scan.py …` for short. The local Gemma server is at
`http://localhost:8000/v1`. Everything is built in a staging folder,
`_import_<name>/`, and nothing in the vault root changes until Marco has read the notes.

The example name is `scan_1997`.

1. **Extract the pages.**
   `journal_scan.py extract attachments/scan_journal_1997.pdf --name scan_1997`
   This copies the PDF's original JPEGs, without recompressing them, to
   `_import_scan_1997/raw/`.

2. **Turn the pages upright.** `journal_scan.py orient scan_1997`
   - Gemma picks a rotation for each page. The upright pages go to `pages/`, with a
     contact sheet, `contact.jpg`.
   - **Gemma is not reliable at this.** On the 1997 notebook it got 5 of 34 pages
     wrong, and it only ever chose the first two options. Pages of drawings with a
     little sideways writing are the hardest. Always look at the contact sheet, and
     look again when reading each page.
   - Fix a page by hand with `--set PAGE=DEGREES` (counter-clockwise), e.g.
     `--set 8=90`. Hand settings are remembered in `orient.json`.
   - Some pages are written in two directions. "Upright" means upright for most of the
     writing; the rest is transcribed as sideways text.

3. **Make the reading views.** `journal_scan.py views scan_1997`
   This writes three images per page to `views/`:
   - `NNN_full.jpg`, the whole page, for the layout;
   - `NNN_top.jpg` and `NNN_bot.jpg`, overlapping halves at full resolution, for
     the words.

   Cut smaller crops yourself for tiny writing, margins, pencil, or a column you
   can't read.

4. **Transcribe the pages yourself, in order.**
   - **Read the images.** For each page, look at the full view, then read every word
     from the halves.
   - **Read in order.** Entries continue across pages, and later pages explain
     earlier ones.
   - **Decide where each entry begins and ends.** Ruled lines, a change of pen or
     pencil, and a new heading usually mark a new entry.
   - **Never draft handwriting with Gemma** (`journal_scan.py transcribe`). In the 1997
     test it missed a whole column, invented words ("street portraits" for "pixel
     portraits") and misread names ("Rome" for "Côme"), so every word had to be
     checked against the image anyway. It is also slow here: about 1½ minutes a page,
     and a page of drawings timed out. The command is kept only for typed pages, or
     for batches too large to read by hand. Its output is a draft to check, never the
     transcription.

5. **Look up what you can, but don't change the text.** Names, titles and references
   identified while reading (e.g. "Côme" is Como, "Anphion faux Mesi" is Apollinaire)
   go in the note's callout. The transcription keeps the page's own spelling.

6. **Write the notes** into `_import_scan_1997/notes/`: one note per entry, in the
   format below. Write them a few pages at a time, as you go, rather than all at the
   end.

7. **Crop the shared pages.** Some pages hold the end of one entry and the start of
   another, or two separate entries. Each note then shows only its own part of the
   page (see "Crops of shared pages").
   - Write the parts in `crops.json`.
   - Run `journal_scan.py crop scan_1997`.
   - Look at every crop.
   - Put each crop in its note, followed by its "Part of" line.

8. **Copy the images** into the vault so the notes show them in Obsidian. Copy new
   files only; never overwrite:
   `cp --update=none _import_scan_1997/pages/*.jpg attachments/pages/`

9. **Check.** `journal_scan.py check scan_1997` must say "all good". It checks that:
   - every page is shown in a note, either whole or as crops;
   - every crop is used in exactly one note and is followed by its "Part of" line;
   - every image exists in `attachments/pages/`;
   - every link to a note leads somewhere;
   - every note has frontmatter with a date.

   The command can't tell whether every line of every page made it into a note. Check
   that yourself, page by page, against the views.

10. **Hand off** to Marco (see "Hand-off" below), and wait for his review. Only after
    he approves:
    - move the notes from `_import_scan_1997/notes/` to the vault root;
    - save `orient.json` and `crops.json` to `tools/settings/` as
      `scan_1997_orient.json` and `scan_1997_crops.json`;
    - delete the `_import_scan_1997/` folder. The page images and crops are already
      in `attachments/pages/`;
    - run `python3 tools/scan_index.py` to update `Scan index.md`;
    - run `python3 tools/build_nav.py` to link the new notes' themes and era and
      regenerate the navigation pages.
    - add the books, essays, poems and articles the new notes mention to
      `tools/bibliography.yaml` (see "Bibliography" below) and run
      `python3 tools/build_bib.py`.

### Replacing notes from an earlier scan

Some notebooks were scanned before these rules existed, in black and white, so their
notes are weaker. When Marco rescans such a notebook:
- **Find the old notes.** `Scan index.md` lists, for every page of every PDF, the notes
  that came from it. Notes whose page was only photographed are listed as `photo-…`.
- **Transcribe the new scan** with the workflow above, in its own staging folder.
- **Replace the old notes only after Marco's review.** Move the old notes into an
  `_replaced/` folder, not to the bin, and keep their dates and `notebook_page`. Then
  move the new notes in and run `tools/scan_index.py`.
- **Keep Marco's later additions.** Old notes can contain retrospective annotations
  he added. Carry them over, or ask.

## Transcription conventions

- Copy line by line within an entry, but join a sentence that wraps across lines into
  one line.
- Keep the page's own lists, arrows and indents: `→ ← ↑ ↓`, `-`, `*`, circled numbers
  (①). Keep `w/`, `&` and `@`.
- **Crossed-out words:** `~~word~~`, when they can still be read. Leave them out when
  they can't.
- **Unclear words:**
  - a word that can't be read: `[?]`
  - an uncertain reading: `word[?]`
  - two possible readings: `[pier/peer?]`
- **Text off the main lines:** inline code with brackets, placed where it belongs,
  e.g. `` `[right margin, sideways: …]` ``, `` `[top, upside down: …]` ``,
  `` `[written later, in pencil: …]` ``.
- **Drawings:** `` `[sketch: what it shows]` `` where the drawing is. Labels written on
  the drawing are quoted inside it: `` `[sketch: a pipe on legs, labelled "recording"]` ``.
- **Underlined words:** mark them with `<u>word</u>`. Keep capitals as written.
- **Pasted-in photographs, tickets and clippings:** describe them in a sentence. Don't
  name or speculate about people in a photo unless the page names them.
- **Anything an editor adds** (a reading note, "continued on p. 14", an identification)
  goes in `` `[…]` ``. It is never mixed into the writing.

## Notes

### One note per entry, and nothing left out

- **One `.md` per entry or idea**, not per page.
- **One page, several entries:** make one note per entry. Each note shows a crop of
  its own part of the page (see "Crops of shared pages" below), never the whole page,
  so a reader can see the note holds everything in its crop.
- **One entry over several pages:** join it into one note, showing all of its pages
  (or crops of them).
- **Only drawings on the page:** make a `visual-record` note that describes them and
  transcribes their labels.
- **Blank pages and stray marks:** no note. List them in the hand-off message instead.
- **Check before handing off:**
  - every line on every page is in exactly one note;
  - every page appears in a note, either whole or as crops that together cover it;
  - every link to another note works.

### Crops of shared pages

- **Where to list them:** `_import_<name>/crops.json` lists, for each shared page, its
  parts in page order as `[top, bottom]` fractions of the page height. A fourth and
  fifth number (`[top, bottom, left, right]`) cut out a column.
- **Making the crops:** `journal_scan.py crop <name>` writes
  `scan_<name>_pNNN_part1.jpg`, `_part2.jpg` … next to the pages.
- **Checking them:**
  - Look at every crop. A crop must hold all of its entry; a line cut in half is a
    failure.
  - Let neighbouring crops overlap a little rather than leave a gap.
- **In the note**, after each crop, link the whole page and the note or notes that
  hold the rest of it:
  ```markdown
  ![[attachments/pages/scan_1997_p030_part2.jpg]]
  *Part of [[attachments/pages/scan_1997_p030.jpg|page 30]]; the rest of the page is in [[1997_p030_Nouveau-Montage-Danse]].*
  ```

### File name

`YYYY-MM-DD_Title-In-Title-Case.md`

- The title has hyphens for spaces and ASCII letters only. Leave out apostrophes,
  accents and `:?/`.
- **Undated pages:** use only the year and the scan page, e.g.
  `1997_p008_Rivers-Trains-and-the-Boulevard-Circulaire.md`. Marco hasn't dated these
  yet.

### Frontmatter

```yaml
---
date: 1997                # YYYY-MM-DD only when written on the page (or certain); else the year
era: Paris, Beaux-Arts
people: [Michel Leiris, Brigitte]
themes: [installation, public-space, museums]
type: journal-fragment     # or visual-record (mostly drawings, photos)
notebook_page: 82          # only the number written on the page, if there is one
scan: scan_1997_p008       # required: the PDF page(s) this note comes from; a list when several
---
```

- **`scan`:** every note made from a notebook page has one. It names the PDF and the
  page's position in it (`scan_<year>[_n]_pNNN`). A page that was only photographed
  is written as `photo-<image name>`. `Scan index.md` is built from this field.
- **`date`:**
  - When a date is written on the page, use it, and use it for the following
    entries until the next one.
  - When an entry's date is only inferred, add `dated: estimated`.
  - **When in doubt, follow the notebook's page order.** An undated entry gets a date
    between the dated entries before and after it, never one that puts it before an
    earlier page or after a later one. Entries with no clue share the date of the last
    dated entry before them; the reading pages then keep them in page order. A clue
    that points elsewhere (a news event, a book's year) doesn't override page order:
    put it in the note's callout and the hand-off, and let Marco decide.
  - The era follows from the date: an entry dated by page order is in the era of
    the pages around it.
- **`era`:** one of the eras in `tools/build_nav.py` (each has a page in `Eras/`):
  Yale, New Haven (to mid-1994) · Summer 1994, Travel and Alps · Final Semester Yale 1995
  (Dec 1994–May 1995) · DC, Post-College (Jun–Oct 1995) · Paris, Beaux-Arts (from 1996) ·
  Japan (Sep–Dec 1998) · New York 2005 · Present, Therapy Notes.
  - Write it as plain text in staged notes; `build_nav.py` turns it into a link.
  - Ask before inventing a new era, and add it to `ERAS` in `tools/build_nav.py`.
- **`people`:**
  - Include people named on the page: friends, family, artists, writers.
  - Use full names when the page gives them, and first names as written for people
    in Marco's life.
  - No one who isn't named on the page.
  - Use `[]` when there is nobody.
- **`themes`:**
  - Use two to five lower-case, hyphenated labels.
  - Reuse existing labels first. See them with:
    `ls Themes/` (themes used 3+ times), or for all of them:
    `grep -h '^themes:' *.md | tr -d '[]"' | sed 's/themes: //' | tr ',' '\n' | sed 's/^ *//' | sort | uniq -c | sort -rn`
  - Add a new label only when nothing fits. A new label should fit one of the subjects
    (theme families) in `tools/build_nav.py`; if it doesn't, add it to `FAMILIES` there.
  - Be strict: a theme belongs to a note only when the note is about it.
  - Write themes as plain text in staged notes. `build_nav.py` links every theme used
    3+ times to its page in `Themes/`, and sets `subjects` from the themes.
- **`subjects`:** generated by `tools/build_nav.py` from the themes. Don't write or edit it.

### Navigation pages

`Themes/`, `Eras/` and `Subjects/` are generated by `python3 tools/build_nav.py`. Each page
is a reading page: every note in the theme, era or subject, in date order, with its
transcription inline. Each entry's title opens the note, and the scan pages are linked
under it. Clicking a theme, era or subject in a note's properties opens its page.
Properties link to these pages by path (`"[[Themes/japan|japan]]"`), because the theme
`japan` and the era `Japan` would otherwise be confused. Never edit these pages by hand;
change `tools/build_nav.py` and run it again.

### Body

```markdown
# Title of the Entry

<the transcription>

---

## Original Page
![[attachments/pages/scan_1997_p008.jpg]]
```

- **The title:**
  - It names what the entry is about, in a few words.
  - It is in the entry's language.
  - It is not a quotation, unless the entry has its own heading.
- **Entries that run onto the next page:** mark where each page starts with a bold
  line, `**Next page:**`. When the entry starts part-way down a page, say where, e.g.
  `**Next page, below the line:**` or `**Top of the next page:**`.
- **Headings and bold labels:** you may add them to give a long list some structure,
  e.g. `**Installation idea:**`. Every word after a label must still be the page's own
  words.
- **The page-image section:**
  - Use `## Original Pages` when there are several images, and put them in page
    order.
  - Show a page whole when the note has all of it. Show a crop when the page is
    shared, followed by its "Part of" line (see "Crops of shared pages").
- **Notes about the transcription:** put them after the transcription and before the
  `---` that comes before the page images, in a short `> [!note]` callout. This covers
  uncertain readings, links to related entries and a guessed date.

### Bibliography

`Bibliography.md` lists every text the notes mention: an index of authors, then each
text's full reference and a quotation of the line in each note that mentions it. It is
generated by `python3 tools/build_bib.py` from `tools/bibliography.yaml`; never edit the
page by hand.
- One YAML entry per text, with `mentions:` mapping each note's file name to a regex
  that finds the reference in it. The script reports a regex that finds nothing.
- Fill in what the note doesn't give (full title, author, publisher, year), and say in
  `guess:` what was guessed and why. Never present a guess as what the note says.
- Texts only: not films, artworks or talks Marco attended (published lectures are fine).

## Hand-off

When the notes are drafted and `check` says "all good", tell Marco:
- how many notes there are, which pages are shared (and so cropped), and which pages
  had no note;
- pages that should be rescanned (blurred, cut off, glare);
- which readings are uncertain;
- any new era or theme labels;
- anything you were unsure how to split or date, and any clue to a date (a news
  event, a book's publication year, a place that suggests a different era).
