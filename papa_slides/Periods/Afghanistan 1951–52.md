# Afghanistan 1951–52

*Write about this period here.*

## Rolls and films

```base
filters:
  and:
    - 'file.hasTag("period/afghanistan-1951-52")'
    - 'type == "roll" || type == "reel"'
views:
  - type: cards
    name: Rolls and films
    order:
      - file.name
    sort:
      - property: sort
        direction: ASC
    image: note.image
    imageFit: contain
    imageAspectRatio: 0.75
    cardSize: 220
```

## Slides

```base
filters:
  and:
    - 'file.hasTag("period/afghanistan-1951-52")'
    - 'file.hasTag("slide")'
views:
  - type: cards
    name: Slides
    order:
      - file.name
    sort:
      - property: sort
        direction: ASC
    image: note.image
    imageFit: contain
    imageAspectRatio: 0.75
    cardSize: 220
```

## Film clips

```base
filters:
  and:
    - 'file.hasTag("period/afghanistan-1951-52")'
    - 'file.hasTag("clip")'
views:
  - type: cards
    name: Clips
    order:
      - file.name
    sort:
      - property: sort
        direction: ASC
    image: note.image
    imageFit: contain
    imageAspectRatio: 0.5625
    cardSize: 220
```

## Notes

