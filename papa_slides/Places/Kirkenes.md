# Kirkenes

In [[Places/Norway|Norway]]. *Write about this place here.* Slides and clips that name it, including the uncertain ones (see each slide's `places_maybe`).

## Slides

```base
filters:
  and:
    - 'file.hasTag("place/kirkenes")'
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
    - 'file.hasTag("place/kirkenes")'
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

