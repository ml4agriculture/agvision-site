# Agriculture-Vision workshop archive (Astro)

A static, independently hostable replica of the public [Agriculture-Vision workshop archive](https://www.agriculture-vision.com/). This is a migration preview, not the live workshop website. No Google Sites runtime, backend, or hosted search is needed. Older submissions, recordings, datasets, and external services remain links to their original destinations.

## Run on your computer

Node.js 22.23.4+ and npm are required for `npm ci`. Node is not required to host the built site.

```sh
npm ci
npm run dev
```

Open <http://127.0.0.1:4321/>. For a production-equivalent preview:

```sh
npm run build
npm run check:parity
npm run preview
```

For self-hosting, serve `dist/` from your static web server with directory indexes (`/path/` resolves to `/path/index.html`) and redirect slashless directory routes as appropriate. This version assumes it is served from the root of its domain. There is no automatic domain change or deployment.

## Content and design

- `src/content/snapshot.json`: editable page records with source URL, title, route, and cleaned HTML; archived 2020–2026 workshop pages and extras.
- `src/content/navigation.json`: display names/order and original archive hierarchy.
- `src/content/inventory.json`: official source discovery baseline for parity checks.
- `public/media/`: local copies of source media. Original outbound links still lead outside the replica.
- `src/layouts/Workshop.astro`, `src/styles/site.css`: shared navigation, local search, layout, and theme.
- `scripts/import-source.py`: importer for the official archive. Review the diff after importing; regenerating can overwrite manual snapshot edits.

Before production cutover, review use rights for third-party logos, portraits, slides, recordings, and Google Sites' default theme artwork; replace or remove anything not cleared for self-hosting. The included typefaces are under their bundled SIL Open Font Licenses. Do not use the migration preview for active submissions without confirming the destination and deadlines.

## Source parity notes

All routes discoverable from the official navigation and same-site page links are included. The official site does not expose a sitemap; unlinked or restricted Google Sites drafts are not part of this public snapshot. Layout is reimplemented in Astro, not a pixel-identical copy of Google's UI. The Google Sites vendor controls are intentionally omitted. Archive content is based on the published text, including historical wording, and is not updated with new schedules or submissions.

The repository MIT license does not relicense third-party assets imported from the workshop archive.
