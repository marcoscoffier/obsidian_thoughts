---
tags: 
  - "theme"
---

# Avant-garde and abstraction

Twentieth-century art against or after the avant-garde: Malevich, Duchamp and Cage, Dubuffet's radicalism, Diebenkorn leaving abstraction, Hopper and Covert against Greenberg.

7 texts. A text is in this theme when its `themes` property links here; add or remove the link to change that.

```base
filters:
  and:
    - file.inFolder("Writings")
    - file.hasLink(this.file)
views:
  - type: table
    name: Writings
    order:
      - file.name
      - year
      - type
      - course
      - words
    sort:
      - property: year
        direction: ASC
```

## Notes

