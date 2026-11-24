---
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
about. 14 texts have no theme; they are listed below.

- [[Experiencing space]] (13) — How space, depth and distance are lived rather than measured
- [[Seen from the air]] (6) — The view from a plane as a new way of seeing
- [[Light, sky and shadow]] (8) — Sunlight, sky colour, twilight and shadow as subject matter
- [[Installations and studio work]] (8) — Texts that belong to his own art
- [[Mirrors and reflection]] (8) — Mirrors, looking-glasses and reflections as the thing being thought about
- [[Word and image]] (6) — Poetry and painting (and music, and film) set side by side
- [[Reality and representation]] (7) — The gap between a real experience and what a poem, a story or a memory can make of it
- [[Avant-garde and abstraction]] (7) — Twentieth-century art against or after the avant-garde
- [[What art is]] (11) — What makes something art, or someone an artist, and how a work is judged
- [[Icons made human]] (3) — Religious images looked at for their humanity
- [[Language and mind]] (8) — The Language and Mind course (Pinker, Jackendoff, Lakoff)
- [[Gender and desire]] (4) — Sex, gender and desire as the subject

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
