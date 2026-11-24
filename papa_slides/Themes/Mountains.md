# Mountains

*Write about this theme here.* Slides are tagged `#theme/mountains` by keyword (see `tools/papa.toml`); check them and set `themes_status: reviewed` once a slide's themes are right.

## Slides

```base
filters:
  and:
    - 'file.hasTag("theme/mountains")'
    - 'file.hasTag("slide")'
views:
  - type: cards
    name: Slides
    order:
      - file.name
      - date
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
    - 'file.hasTag("theme/mountains")'
    - 'file.hasTag("clip")'
views:
  - type: cards
    name: Clips
    order:
      - file.name
      - date
    sort:
      - property: sort
        direction: ASC
    image: note.image
    imageFit: contain
    imageAspectRatio: 0.5625
    cardSize: 220
```

## Notes

