---
tags:
  - subject
---

# Making Art

Pieces, proposals, studio work: installation, sculpture, painting, photography, video.

Themes: [[bricolage]], [[collage]], [[craft]], [[creativity]], [[dance]], [[drawing]], [[gesture]], [[installation]], [[land-art]], [[materiality]], [[painting]], [[painting-concepts]], [[painting-process]], [[painting-technique]], [[photography]], [[pixels]], [[project-list]], [[sculpture]], [[sculpture-ideas]], [[studio-practice]], [[video]]

```base
filters:
  and:
    - file.hasLink(this.file)
    - not:
        - file.inFolder("Themes")
        - file.inFolder("Eras")
        - file.inFolder("Subjects")
views:
  - type: table
    name: Notes
    order:
      - file.name
      - date
      - era
      - themes
      - people
    sort:
      - property: date
        direction: ASC
```
