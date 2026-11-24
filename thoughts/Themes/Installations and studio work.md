---
tags: 
  - "theme"
---

# Installations and studio work

Texts that belong to his own art: printed directions handed to viewers, labels, sketches for pieces, notes toward sculpture, the Beaux-Arts statement.

*Left out:* 'Transparency' (two words) may belong here, but nothing in it says so.

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

