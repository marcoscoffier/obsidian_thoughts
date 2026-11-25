---
tags:
  - field
---

# Mathematics

Calculus, linear algebra, differential equations, probability, analysis.

```base
filters:
  and:
    - file.hasLink(this.file)
    - not:
        - file.inFolder("Fields")
views:
  - type: table
    name: Notes
    order:
      - file.name
      - date
      - field
      - topics
      - source
    sort:
      - property: date
        direction: ASC
```
