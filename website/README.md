# ImperaOS Website

**ImperaOS** (Agent Control Plane) için kurumsal, **Türkçe** one-page tanıtım sitesi.

## Design system

Generated with [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill):

- **Pattern:** Enterprise Gateway + Trust & Authority
- **Palette:** Authority navy (`#0B1F3A` / `#1E3A8A`) + trust amber (`#B45309`)
- **Typography:** IBM Plex Sans + IBM Plex Mono
- **Persisted tokens:** `../design-system/imperaos/MASTER.md`

Anti-patterns avoided: playful UI, AI purple/pink gradients, hidden credentials.

## Preview

```bash
# From this directory
python3 -m http.server 5180
# open http://localhost:5180
```

Or open `index.html` directly in a browser.

## Structure

```
website/
├── index.html
├── css/styles.css
├── js/main.js
└── README.md
```

Static only — no build step required.
