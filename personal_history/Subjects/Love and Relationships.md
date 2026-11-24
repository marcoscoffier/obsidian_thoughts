---
tags:
  - subject
---

# Love and Relationships

Katherine, love, friendship, letters.

Themes: [[address-book]], [[commitment]], [[endings]], [[friendship]], [[intimacy]], [[katherine]], [[letters]], [[love]], [[marriage-crisis]], [[marriage-distance]]

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
