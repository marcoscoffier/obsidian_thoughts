---
tags:
  - subject
---

# Language and Literature

Reading, writing, poetry, French, language and signs.

Themes: [[communication]], [[ekphrasis]], [[finnegans-wake]], [[french]], [[imagination]], [[language]], [[literature]], [[metaphor]], [[poetry]], [[reading]], [[reading-list]], [[semiotics]], [[writing-process]], [[writing-style]]

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
