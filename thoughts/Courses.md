---
tags:
  - home
---

# Courses

The Yale courses the papers were written for, as named on their cover sheets.
Texts with no course are his own writing, transcriptions, or undated.

```base
filters:
  and:
    - file.inFolder("Writings")
    - '!course.isEmpty()'
views:
  - type: table
    name: By course
    order:
      - course
      - file.name
      - year
      - teacher
      - section
      - type
    sort:
      - property: course
        direction: ASC
      - property: date
        direction: ASC
```
