---
tags:
  - era
---

# Final Semester Yale 1995

Senior year at Yale: the thesis pieces, Ron Jones's lectures, the break-up with Katherine. 1994-12 – 1995-04. 89 notes.

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
