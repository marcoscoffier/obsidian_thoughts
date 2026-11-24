---
tags: 
  - "theme"
---

# Icons made human

Religious images looked at for their humanity: the ivory Christ whose lost arms make him more human, Taddeo's veiny John the Baptist against Nardo's, Giovanni da Milano's emotional Joachim and Anna.

3 texts. A text is in this theme when its `themes` property links here; add or remove the link to change that.

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

