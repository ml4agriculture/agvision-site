# Workshop edition template

The 2027 route is an explicit opt-in to the new template. Historical routes still
use their imported snapshot and the existing Workshop layout unchanged.

## Authoring and composition

`src/content/editions/*.json` is the edition collection, loaded by Astro's `glob`
loader. `src/lib/edition-schema.ts` validates it at build time and supplies the
TypeScript props. Plain text is escaped by Astro; HTML strings are not accepted.
Keep confidential proposal material and correspondence outside the repository.

| File / block | Responsibility |
| --- | --- |
| `layouts/EditionPage.astro` | Compose the page, build calendar data, generate section links, pass SEO metadata to the shared layout |
| `edition/EditionHero.astro` | Exact workshop title, theme, image and conference context |
| `edition/EditionIntro.astro` | Optional notice and navigation to rendered sections |
| `edition/EditionOverview.astro` | Overview copy and a named `status` slot |
| `edition/EditionStatus.astro` | Acceptance, assigned schedule, optional notification reference and calendar |
| `edition/EditionSpeakers.astro` | Optional confirmed public speaker list |
| `edition/EditionFocus.astro` | Optional research areas |
| `edition/EditionArchive.astro` | Optional links to prior editions |
| `edition/SectionHeading.astro` | Shared accessible section heading |
| `WorkshopCalendar.astro` | Static Google Calendar and .ics links, or pending text |
| `edition/LocalSchedule.tsx` | Small React enhancement showing confirmed times in the visitor's timezone |

Component paths in the table are under `src/components/` unless a layout is
specified. CSS is in `src/styles/edition.css`, scoped beneath `.workshop-edition`;
it loads only with the edition template. Shared theme variables come from the
existing site stylesheet. Blocks can also be composed directly in another Astro
page, with that wrapper and stylesheet. Use one instance of each block per page
so its section IDs remain unique. The default template's trailing slot accepts
additional edition-specific content.

The `speakers`, `research`, `archive`, and `notice` properties are optional.
Omitting a block also omits its section link. Preserve verified status copy;
changing a schedule to confirmed does not establish workshop acceptance.
`noIndex` defaults to true, and explicit routes avoid automatically publishing
all content records. Indexability, navigation, search and release remain separate
reviewed changes. Noindex is not access control.

## Rendering and loading boundaries

| Work | When it runs | Data sent to the browser |
| --- | --- | --- |
| Collection load and schema validation | Build time | Rendered public content |
| Astro sections and calendar generation | Build time | HTML and confirmed static .ics file |
| LocalSchedule React island | Server render at build; hydrate with `client:visible` | Only start/end strings, then browser locale/timezone |
| Existing site navigation/search | Existing client scripts | Existing static archive search index |

A pending schedule renders no React island, no Google Calendar action and no
.ics route. A confirmed schedule includes its host-time display and functional
calendar links in HTML, even when JavaScript is disabled or hydration fails.
The React island starts with the same server/client fallback, then reads browser
preferences in an effect to avoid hydration mismatches. It never fetches an API
or imports the full edition record/calendar generator into the browser bundle.

Use `client:visible` for optional enhancements below the fold. Reserve
`client:load` for immediately required interaction. Keep static text, speakers,
links and layout in Astro; additional React islands should own independent
interactive state. Avoid `client:only` for essential content.

The project retains `output: 'static'` and the current Cloudflare asset setup.
There is no new backend or client data waterfall. If future data requires live
per-request loading (e.g. authenticated registration), that is a separate change
with a compatible adapter and a documented server boundary. `server:defer`
requires server rendering support; it is not useful for this local static data.
See [Astro islands](https://docs.astro.build/en/concepts/islands/),
[client directives](https://docs.astro.build/en/reference/directives-reference/#client-directives),
and [server islands](https://docs.astro.build/en/guides/server-islands/).

## Adding an edition

1. Create a JSON record under `src/content/editions/` using 2027 as the shape,
   replacing every editorial field with verified public content. Give it a new
   `path`, `year`, stable calendar `uid`, and official `url`; review all labels,
   title prefix, notice, status and archive links. Omit unavailable optional blocks.
2. Start with `schedule: { "status": "pending" }` and `noIndex: true`. Confirmed
   schedules require offset-bearing start/end, an IANA timezone and UTC updatedAt;
   calendar validation rejects incorrect dates, offsets or reversed ranges.
3. Add an explicit route using the content filename as its entry ID:

   ```astro
   ---
   import { getEntry } from 'astro:content';
   import EditionPage from '../layouts/EditionPage.astro';
   const entry = await getEntry('editions', 'YOUR_EDITION_ID');
   if (!entry) throw new Error('Missing edition content');
   ---
   <EditionPage edition={entry.data} />
   ```

4. Copy the existing `[calendar].ics.ts` endpoint into that route's directory,
   changing its `getEntry` ID. Keep the basename `workshop.ics`; the calendar
   helper derives the download path and filename from the edition's `path`.
   The page route and `path` must match. No endpoint is generated while pending.
5. Run `npm run check`, `npm run test:edition`, `npm run test:calendar`,
   `npm run build`, `npm run check:parity`, and `npm run check:2027`. Review both
   mobile and desktop. Any release remains an explicit separate action.

The calendar integration test builds a separate fictitious 2030 edition with
optional sections omitted, verifies its own URLs and deferred React island,
then switches only that temporary fixture to pending and checks removal.
Set `AGVISION_TEST_ARTIFACTS` to an outside-repository directory to preserve the
fictitious confirmed build for local browser QA; never deploy that test build.
