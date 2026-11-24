---
tags:
  - subject
---

# Places and Cities

Places, cities, travel, landscape and nature.

Themes: [[alps]], [[architecture]], [[city]], [[flight]], [[japan]], [[landscape]], [[maps]], [[nature]], [[place-attachment]], [[public-space]], [[tignes]], [[travel]], [[urbanism]], [[yale]], [[yale-culture]]

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
