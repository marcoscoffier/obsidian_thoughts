---
tags:
  - field
---

# Electrical Engineering

Circuits, signals, electronics, antennas, control.

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
