---
tags:
  - subject
---

# Mind, Science and Systems

Cognition, systems, technology, mathematics and science.

Themes: [[art-vs-science]], [[cognition]], [[engineering]], [[epistemology]], [[internet]], [[knowledge]], [[play]], [[systems]], [[technology]]

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
      - era
      - themes
      - people
    sort:
      - property: date
        direction: ASC
```
