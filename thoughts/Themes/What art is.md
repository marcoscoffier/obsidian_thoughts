---
tags: 
  - "theme"
---

# What art is

What makes something art, or someone an artist, and how a work is judged: the essay on the word 'artist', Balzac's unknown masterpiece, Gautier's theory, Kant's taste, Hegel's ranking, Lu Chi's poetics, Proust's artistic process, the Beaux-Arts statement of motives.

11 texts. A text is in this theme when its `themes` property links here; add or remove the link to change that.

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

