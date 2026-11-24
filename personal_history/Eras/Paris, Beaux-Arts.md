---
tags:
  - era
---

# Paris, Beaux-Arts

Student at the École nationale supérieure des Beaux-Arts in Paris (from 1996). 1997 – 1999-06. 117 notes.

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
