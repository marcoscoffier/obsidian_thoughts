---
tags: 
  - "theme"
---

# Seen from the air

The view from a plane as a new way of seeing: Saint-Exupéry, the mountain climbed versus the mountain flown around, the ocean crossing in the senior essay notes.

*Left out:* The Meinel letter mentions an observer aloft only as a point in a refraction diagram.

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

