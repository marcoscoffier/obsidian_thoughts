---
tags:
  - subject
---

# Art Theory and the Art World

Ideas about art, criticism, art history, the art world and culture at large.

Themes: [[aesthetics]], [[art-history]], [[art-theory]], [[coursework]], [[criticism]], [[film]], [[history]], [[mass-culture]], [[modernism]], [[painting-theory]], [[politics]], [[representation]], [[studio-critique]], [[television]]

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
