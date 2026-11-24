---
tags:
  - era
---

# Japan

The stay in Japan, September–December 1998 (Tokyo, Musabi, Miwa's family). 1998-10. 7 notes.

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
