# Papa's slides

Slides from Dad's rolls (1951–1971) and clips from his Super 8 films, with the
descriptions from the READMEs in `~/Pictures/Papa`.

- [[Timeline]]: every roll and film in date order
- **Periods**: [[Periods/Afghanistan 1951–52]] · [[Periods/Rome and Paris 1952]] · [[Periods/Iran 1955–65]] · [[Periods/Later years]]
- **Themes**: [[Themes/Road trips]] · [[Themes/Mountains]] · [[Themes/Markets]] · [[Themes/Locals]] · [[Themes/Sheep herders]]

## Languages

Captions come in a blue **English** box and a red **Français** box. To show only
one language: *Settings → Appearance → CSS snippets*, turn on `papa-hide-fr`
(English only) or `papa-hide-en` (French only).

## Updating

The READMEs are the source of truth. After changing a README, adding slides or
adding a roll in `~/Pictures/Papa`, run:

    python3 tools/build_vault.py --dry-run   # see what would change
    python3 tools/build_vault.py

What you write under **Notes** in any note is kept, and so are your own
properties and tags. Theme tags are keyword guesses until you set
`themes_status: reviewed` on a slide; after that the script leaves them alone.

## Notes

