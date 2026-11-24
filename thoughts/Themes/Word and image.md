---
tags: 
  - "theme"
---

# Word and image

Poetry and painting (and music, and film) set side by side: ekphrasis, the Word and Image papers, Hegel's ranking of the arts, the writer's domain against the painter's.

6 texts. A text is in this theme when its `themes` property links here; add or remove the link to change that.

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

