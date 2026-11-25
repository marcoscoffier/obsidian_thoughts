---
tags:
  - home
---

# Technical Notes

Marco's notes on mathematics, physics, electrical engineering and machine learning:
notebooks and course notes transcribed from scans, and notes written since.

Each note's `field` links to one of the pages below, which lists every note in that
field. Click a field in a note's properties to get there.

- [[Mathematics]]
- [[Physics]]
- [[Electrical Engineering]]
- [[Machine Learning]]

Every note, newest first:

```base
filters:
  and:
    - file.hasProperty("field")
views:
  - type: table
    name: All notes
    order:
      - file.name
      - date
      - field
      - topics
      - source
    sort:
      - property: date
        direction: DESC
```
