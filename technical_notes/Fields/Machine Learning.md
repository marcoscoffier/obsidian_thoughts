---
tags:
  - field
---

# Machine Learning

Statistics, optimisation, models and training.

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
