---
tags:
  - era
---

# Summer 1994, Travel and Alps

The road trip and the summer in France and the Alps (Tignes, Annecy, Mont Blanc). 1994-07 – 1994-08. 41 notes.

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
