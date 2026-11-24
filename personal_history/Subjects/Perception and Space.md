---
tags:
  - subject
---

# Perception and Space

Seeing, light, space and the instruments that change them.

Themes: [[arnheim]], [[clouds]], [[color-theory]], [[framing]], [[gestalt]], [[illusion]], [[light]], [[mirrors]], [[observation]], [[optics]], [[perception]], [[perspective]], [[sky]], [[space]], [[time]], [[turrell]]

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
