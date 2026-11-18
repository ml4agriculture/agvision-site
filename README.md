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

## Production visit analytics

1. In [Cloudflare Web Analytics](https://developers.cloudflare.com/web-analytics/get-started/),
   add `agvision-site.leandro-g-almeida.workers.dev` as a site with **manual**
   setup. Do not enable automatic beacon injection for the same site.
2. Copy the public site token from the snippet (not a Cloudflare API token).
   In the `agvision-site` Worker's **Settings → Builds → Variables and secrets**,
   set `PUBLIC_CF_WEB_ANALYTICS_TOKEN` for production builds only. Do not set it
   for previews or as a runtime binding. Rebuild production to activate the tag.
3. Open the production site over HTTPS, then look for visits and page views in
   Cloudflare Web Analytics. Counts are shown in the dashboard, not on the site.

The site omits analytics when the token is missing. Even a production build
only loads the beacon at the exact HTTPS production hostname, not at a PR
preview, a local address, or the current Google Sites domain. If the canonical
domain moves to this Worker, register the actual production hostname in
Cloudflare Web Analytics and review the allowlist in
`src/components/ProductionAnalytics.astro` before collecting there.

## Cloudflare Workers pull-request previews

In the existing `agvision-site` Worker's **Settings → Builds**, keep `main`
as the production branch and use `npm run build` as the build command. Enable
preview builds for non-production branches and set only the **Preview deploy
command** to:

```sh
npx --yes wrangler@4.164.0 preview
```

`wrangler.jsonc` serves Astro's `dist/` as static assets. The preview command
publishes to the Worker's preview hostname on `workers.dev`, not the live
custom domain. Leave the existing production deploy command and DNS unchanged.
Keep preview branch filters scoped to the branches you want Cloudflare to build.
See [Workers Builds branch settings](https://developers.cloudflare.com/workers/ci-cd/builds/build-branches/).

## Content and design

### Unpublished 2027 edition

The local draft is at `/agriculture-vision-2027/`, implemented in
`src/pages/agriculture-vision-2027.astro`. It uses the existing workshop theme
and leaves the current homepage and all 2020–2026 archive content intact.
The draft marks acceptance and the workshop date as unconfirmed and contains
only an overview of the proposed research scope. It does not announce a
lineup, program, submission deadline, format, or sponsors.

To review the built draft:

```sh
npm run build
npm run check:parity
npm run check:2027
npm run test:calendar
npm run preview -- --port 4327
```

Open <http://127.0.0.1:4327/agriculture-vision-2027/>. The draft is absent from
the public navigation and search index; there is currently no generated
sitemap. Preserve this exclusion if a sitemap is added. Its `noindex, nofollow`
metadata requests search-engine exclusion; it is **not access control**.
Production analytics are omitted for the draft. Do not store private proposal
documents or correspondence in this repository.

Before release, confirm acceptance, the assigned workshop date, approved
public copy, and any program or participation details with the organizers.
Then make publication and the homepage/navigation change an explicit,
separate update. This draft does not change Cloudflare, DNS, or deployment
configuration.

#### Calendar links

`src/content/workshop-2027.json` is the single source for calendar metadata and
schedule status. Keep `schedule.status` as `pending` until the assigned workshop
schedule is confirmed. Pending state renders only an explanatory sentence;
neither a Google Calendar link nor a `.ics` route/file is generated.

Once confirmed, set `schedule.status` to `confirmed` and provide `start` and
`end` as ISO date/times with seconds and explicit offsets, `timeZone` as an IANA
timezone name, and `updatedAt` as the UTC revision time ending in `Z`. The local
date/time and offset must agree with that timezone, including daylight saving.
Include `schedule.location` only after a venue is known. Set `url` to the
approved official workshop page (currently the existing official homepage),
retain the stable `uid`, and update the page's acceptance copy as part of release.

A confirmed build adds accessible Google Calendar and `.ics` download links
to the workshop status panel. Both carry the same title, official URL, start
and end; unknown location is omitted. The `.ics` uses UTC instants, escaped
text, CRLF line endings and UTF-8-aware line folding per
[RFC 5545](https://www.rfc-editor.org/rfc/rfc5545). Visitors choose whether to
save it in their calendar; the site does not create events or send invitations.

`npm run test:calendar` checks DST conversion, escaping/folding, invalid input,
and both output formats. It also builds a fictitious confirmed event in a
temporary directory, then rebuilds that fixture as pending to verify removal
of links and downloads. It never modifies the real pending schedule or opens
a calendar service.

### Archive sources

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
