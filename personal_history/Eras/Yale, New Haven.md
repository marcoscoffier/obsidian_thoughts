---
tags:
  - era
---

# Yale, New Haven

College years in New Haven, up to the summer of 1994. 1992-12 – 1994-10. 59 notes.

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
