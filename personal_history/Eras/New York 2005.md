---
tags:
  - era
---

# New York 2005

A new start in New York in 2005: the phone and dialog projects, almost-something. 2005-03 – 2005-04. 16 notes.

```base
filters:
  and:
    - file.hasLink(this.file)
    - not:
        - file.inFolder("Themes")
        - file.inFolder("Eras")
        - file.inFolder("Subjects")
views:
  - type: table
    name: Notes
    order:
      - file.name
      - date
      - themes
      - people
    sort:
      - property: date
        direction: ASC
```
