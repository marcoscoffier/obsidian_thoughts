---
tags: 
  - "theme"
---

# Reality and representation

The gap between a real experience and what a poem, a story or a memory can make of it: Wordsworth's leech-gatherer, Stevens's 'poem of pure reality', Woolf's and Hoffmann's glasses, Proust's goodnight kiss, a happy morning that a poem could not convey.

*Left out:* Ulysses ends on 'a type of simulated reality', but the paper is about repetition; left out.

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

