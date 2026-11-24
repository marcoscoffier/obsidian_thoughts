---
tags:
  - era
---

# DC, Post-College

Washington DC after graduation: the NEA, Jackson, the letters to Katherine. 1995-06 – 1995-10. 32 notes.

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
