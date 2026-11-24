---
tags: 
  - "theme"
---

# Mirrors and reflection

Mirrors, looking-glasses and reflections as the thing being thought about: Woolf's looking-glass, Hoffmann's glass darkly, Ashbery's convex mirror and Merrill's mirror, confession held up as a mirror, the mirrored installations.

8 texts. A text is in this theme when its `themes` property links here; add or remove the link to change that.

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

