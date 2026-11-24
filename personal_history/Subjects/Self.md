---
tags:
  - subject
---

# Self

Feelings, fears, ambition, identity, the body, dreams.

Themes: [[ambition]], [[body]], [[dreams]], [[ego]], [[fear]], [[gender]], [[identity]], [[memory]], [[mortality]], [[mountain-biking]], [[religion]], [[retrospective-self]], [[self-awareness]], [[self-criticism]], [[social-alienation]], [[solitude]], [[stereotypes]], [[synchronicity]], [[therapy]], [[vocation]]

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
