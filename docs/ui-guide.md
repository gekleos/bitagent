# Dashboard UI Guide

BitAgent ships a self-contained operator dashboard built on FastAPI and vanilla
JavaScript. The dashboard is the primary interface for monitoring indexer health,
browsing your torrent library, managing search targets, reviewing evidence
events, and configuring runtime settings. This guide covers installation,
authentication, every tab in detail, keyboard shortcuts, and theming.

## Dashboard overview

The dashboard (`bitagent-ui`) is a thin presentation layer that communicates
with the BitAgent core via its GraphQL API and maintains a local SQLite sidecar
for operator overrides, audit logging, and poster caching. It never mutates
indexing data directly — all structural changes flow through the GraphQL API.

Six primary tabs organize the interface:

1. **Dashboard** — real-time stat cards, category breakdown, system health
   indicators, and an activity feed.
2. **Library** — poster grid or list view of indexed torrents with search,
   filters, and a detail modal.
3. **Wants** — operator-defined search targets with priority and status
   management.
4. **Evidence** — webhook event log showing how *arr feedback flows back into
   the classifier.
5. **Settings** — six sub-tabs covering configuration, auth, integrations,
   retention, classifier tuning, and audit history.
6. **System** — health checks, Torznab endpoint tester, GraphQL explorer, and
   raw Prometheus metrics.

## Installation

### Prerequisites

- Docker 24.0+ and Docker Compose v2.24+
- A running BitAgent core instance with its GraphQL API accessible
- At least 512 MB RAM allocated to the dashboard container
- Network connectivity between the dashboard and the BitAgent core

### Docker Compose setup

The standard deployment bundles the dashboard alongside the core. Retrieve the
compose file and create an environment file:

```bash
curl -O https://raw.githubusercontent.com/gekleos/bitagent/main/examples/compose.public.yml
```

Create a `.env` file with the minimum required variables:

```env
DASHBOARD_API_KEY=$(openssl rand -hex 32)
TORZNAB_API_KEY=$(openssl rand -hex 32)
BITAGENT_GRAPHQL_URL=http://bitagent:3333/graphql
BITAGENT_METRICS_URL=http://bitagent:3333/metrics
POSTGRES_DB=bitagent
POSTGRES_USER=bitagent
POSTGRES_PASSWORD=<strong_password>
```

Deploy:

```bash
docker compose -f compose.public.yml up -d
```

Wait approximately 3 minutes for the DHT bootstrap to complete, then open
`http://localhost:8080` in your browser.

### First run

On first load the dashboard displays a one-time confirmation banner showing the
active `DASHBOARD_API_KEY`. Copy this value to your password manager. The
banner does not reappear after dismissal.

The dashboard creates its SQLite sidecar at `/data/bitagent-ui.db` on first
boot. This file stores operator overrides, audit log entries, and cached TMDB
poster URLs. Back up this file alongside your Postgres dumps if you want to
preserve settings and audit history across migrations.

## Configuration

All dashboard behavior is controlled via environment variables passed to the
`bitagent-ui` container. The table below documents every supported variable.

### Core connection

| Variable | Default | Description |
|---|---|---|
| `BITAGENT_GRAPHQL_URL` | `http://bitagent:3333/graphql` | Full URL to the BitAgent core GraphQL endpoint. The dashboard routes all data fetches through this URL. |
| `BITAGENT_METRICS_URL` | `http://bitagent:3333/metrics` | Prometheus metrics endpoint on the core. Powers the System tab gauges and the Dashboard stat cards. |

### Authentication

| Variable | Default | Description |
|---|---|---|
| `REQUIRE_AUTH` | `true` | Master toggle. Set to `false` to disable all authentication (use only on fully isolated networks). |
| `DASHBOARD_API_KEY` | *(none)* | Primary API key for dashboard access. Validated via `Authorization: Bearer <key>` header or `?apikey=<key>` query parameter. |
| `TORZNAB_API_KEY` | *(none)* | Separate key for the Torznab endpoint. Keeps dashboard and indexer auth independent for rotation safety. |
| `TRUST_NPM_HEADERS` | `false` | When `true`, trusts `X-Auth-User-Id` and `X-Auth-User-Email` headers injected by Nginx Proxy Manager or similar reverse proxies. |
| `TRUST_FORWARDED_USER` | `false` | When `true`, trusts the `X-Forwarded-User` header for generic reverse-proxy SSO setups (Authelia, Authentik, etc.). |
| `SSO_COOKIE_NAME` | *(none)* | Cookie name to read for SSO session validation. The dashboard decodes the cookie value as a signed JWT or opaque token depending on your SSO provider. |

### Integrations

| Variable | Default | Description |
|---|---|---|
| `TMDB_API_KEY` | *(none)* | Optional. Enables poster art fetching from TMDB for the Library tab. Leave empty to disable external poster lookups entirely. Cached in the SQLite sidecar for 7 days. |

### Logging

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `info` | Controls dashboard log verbosity. Accepted values: `debug`, `info`, `warn`, `error`. Set to `debug` to trace auth resolver decisions and GraphQL query timing. |

## Authentication

The dashboard implements a 4-tier authentication resolver that evaluates
credentials in strict priority order. The first tier that produces a valid
identity wins; subsequent tiers are skipped.

### Tier 1: API key

The highest-priority resolver. Checks for `DASHBOARD_API_KEY` in the
`Authorization: Bearer <key>` header or the `?apikey=<key>` query parameter.
Validation uses constant-time comparison to prevent timing attacks. When
matched, the request identity resolves to `api-client` with full dashboard
access.

This is the default and recommended authentication method for most deployments.
It requires no reverse proxy, no SSO provider, and integrates natively with
*arr client token fields.

### Tier 2: Reverse-proxy headers (NPM)

Activated when `TRUST_NPM_HEADERS=true`. Reads `X-Auth-User-Id` and
`X-Auth-User-Email` headers injected by Nginx Proxy Manager after its own
authentication flow. The dashboard trusts these headers unconditionally when
enabled, so only activate this tier behind a proxy you fully control.

The resolved identity uses the header values directly — the user ID becomes the
audit actor, and the email populates the Settings audit log.

### Tier 3: Forwarded user

Activated when `TRUST_FORWARDED_USER=true`. Reads the `X-Forwarded-User`
header, which is the standard header used by Authelia, Authentik, Caddy
`forward_auth`, and Traefik `ForwardAuth`. This tier covers generic
reverse-proxy SSO setups where the proxy authenticates the user and injects a
single identity header.

### Tier 4: SSO cookie

Activated when `SSO_COOKIE_NAME` is set to a non-empty value. The dashboard
reads the named cookie from the request and decodes it as a session token. This
tier is the fallback for environments where headers are stripped by intermediate
proxies but cookies survive the hop.

### Resolution order and fallback

```text
Request arrives
  -> Tier 1: API key present?       -> YES -> identity = "api-client"
  -> Tier 2: NPM headers trusted?   -> YES -> identity = header values
  -> Tier 3: Forwarded user trusted? -> YES -> identity = header value
  -> Tier 4: SSO cookie present?     -> YES -> identity = cookie payload
  -> All tiers exhausted             -> 401 Unauthorized
```

When `REQUIRE_AUTH=false`, the resolver is bypassed entirely and all requests
resolve to an anonymous identity. This mode is intended for development and
fully isolated LAN deployments only.

## Dashboard tab

The landing view after login. Designed for at-a-glance operational awareness
without requiring drill-down into individual tabs.

### Stat cards

Four summary cards span the top of the page:

- **Total torrents** — count of unique infohashes in the Postgres index.
- **Active DHT peers** — current peer count from the core's routing table.
- **Indexer throughput** — torrents indexed per minute, averaged over the last
  5 minutes.
- **Cache hit ratio** — percentage of GraphQL queries served from cache vs.
  Postgres.

Each card displays the current value prominently with a small delta indicator
showing the change over the last hour. Green arrows indicate improvement; red
arrows indicate degradation.

### Category breakdown

A horizontal bar chart showing the distribution of indexed torrents across
content categories (TV, Movies, Music, Books, Software, Other). Hover over a
bar to see the exact count and percentage. Categories are derived from the CEL
classifier output.

### System health

A compact status row with colored pills:

- **Green** — all services healthy, DHT peers above threshold, no errors.
- **Yellow** — degraded performance (high latency, low peer count, cache
  pressure).
- **Red** — service unreachable, database connection failed, or critical error
  in the last 5 minutes.

Each pill links to the corresponding System tab health check for deeper
diagnostics.

### Activity feed

A reverse-chronological stream of the most recent operational events:

- Torrents indexed (with infohash prefix and category)
- Evidence webhook received (with *arr instance name)
- Classifier decisions (preempt vs. full pipeline)
- Settings changes (key, actor, timestamp)
- Authentication events (logins, failed attempts)

The feed auto-refreshes every 30 seconds. Click any entry to navigate to its
detail view in the relevant tab.

## Library tab

The primary content browser for your indexed torrent collection.

### View modes

Toggle between two layouts using the view switcher in the top-right corner:

- **Poster grid** — card-based layout showing TMDB poster art (when
  `TMDB_API_KEY` is configured), title, category badge, seeder count, and
  classifier confidence score. Cards are arranged in a responsive grid that
  adapts to viewport width.
- **List view** — dense table layout with sortable columns: title, category,
  size, seeders, leechers, classifier confidence, indexed date, and evidence
  count. Click any column header to sort ascending; click again for descending.

### Search

The search bar accepts free-text queries and returns results ranked by
classifier confidence and evidence score. Searches route through the core's
GraphQL `searchTorrents` resolver. Results update as you type with a 300ms
debounce.

Search supports qualifier syntax for precision filtering:

- `category:tv` — restrict to a specific category
- `resolution:1080p` — filter by resolution tag
- `seeders:>50` — minimum seeder threshold
- `confidence:>0.8` — minimum classifier confidence

### Filters

The filter sidebar (collapsible on mobile) provides faceted filtering:

- **Category** — checkbox list (TV, Movies, Music, Books, Software, Other)
- **Resolution** — checkbox list (2160p, 1080p, 720p, SD)
- **Source** — checkbox list (WEB-DL, WEBRip, BluRay, HDTV, etc.)
- **Date range** — indexed-date picker with preset ranges (24h, 7d, 30d, 90d)
- **Evidence status** — has evidence, no evidence, confirmed, rejected

Filters compose with AND logic. Active filters display as removable chips above
the results.

### Torrent detail modal

Click any torrent to open a full-detail modal overlay:

- **Header** — title, poster art, category badge, and magnet link copy button.
- **Metadata** — resolution, source, codec, audio channels, HDR format, file
  count, total size.
- **Classification** — confidence score, rule chain trace showing which CEL
  rules fired, and whether evidence preempted the pipeline.
- **Evidence history** — list of all webhook events associated with this
  infohash, with timestamps, *arr instance names, and grab/fail status.
- **Seeder graph** — sparkline showing seeder count over the last 30 days.
- **Actions** — copy magnet URI, open in external tracker, flag for manual
  review.

Press `Esc` or click outside the modal to close.

## Wants tab

Operator-defined search targets. A "want" is a content item you are actively
seeking — BitAgent's Wantbridge routes DHT queries to seeders matching your
explicit requests, bypassing generic keyword matching.

### Creating a want

Click the **New Want** button in the top-right corner. The creation form
accepts:

- **Title** — free-text name for the want (e.g., "Severance S02E08").
- **Type** — dropdown: TV Episode, TV Season, Movie, Music Album, Book.
- **Identifiers** — optional TVDB ID, TMDB ID, or IMDB ID for precise
  matching.
- **Quality profile** — minimum resolution, preferred source, codec
  preferences.
- **Priority** — integer from 1 (highest) to 99 (lowest). Lower numbers are
  resolved first when multiple wants match the same seeder pool.
- **Notes** — free-text operator notes visible in the wants list.

### Status management

Each want has a lifecycle status:

- **Active** — Wantbridge is actively routing queries for this item.
- **Snoozed** — temporarily paused; resumes on the specified wake date.
- **Fulfilled** — matched and confirmed via evidence webhook. Automatically
  set when a grab event arrives.
- **Cancelled** — manually retired by the operator.

Bulk actions allow selecting multiple wants and applying status changes, priority
adjustments, or deletion in a single operation.

### Want list

The wants list displays all items with columns for title, type, priority,
status, created date, and last-matched date. Sort by any column. The search
bar filters wants by title or identifier. Status pills use color coding: green
for fulfilled, blue for active, yellow for snoozed, gray for cancelled.

## Evidence tab

The evidence pipeline is BitAgent's feedback loop: *arr clients emit webhooks
on successful downloads, and those events propagate ground-truth labels back
into the classifier. The Evidence tab provides full visibility into this
pipeline.

### Webhook event log

A reverse-chronological table of every webhook payload received:

- **Timestamp** — when the webhook arrived at the evidence endpoint.
- **Source** — which *arr instance sent the event (e.g., "sonarr-prod",
  "radarr-4k").
- **Event type** — `Grab`, `Download`, `Rename`, `Delete`, or `Test`.
- **Infohash** — the torrent infohash associated with the event.
- **Title** — the resolved title from the *arr payload.
- **Status** — whether the event was accepted, deduplicated, or rejected with
  the reason.

Click any row to expand the full JSON payload for debugging.

### How the *arr feedback loop works

The evidence pipeline operates in four stages:

1. **Ingestion** — *arr sends a webhook to
   `POST /evidence/arr/<instance_name>`. The dashboard validates the payload
   schema and deduplicates against recent events (burst suppression).

2. **Label extraction** — successful download events carry ground-truth
   identifiers (TVDB ID, TMDB ID, IMDB ID, season/episode numbers). These
   are extracted and normalized across *arr version differences.

3. **Classifier preempt** — the ground-truth label is written to the evidence
   store and propagated to the CEL classifier. On subsequent encounters with
   the same infohash, the classifier short-circuits its full rule chain and
   applies the evidence label directly. This is the core mechanism that
   reduces false positives over time.

4. **Penalty weighting** — failed download events (quality rejections, import
   failures) apply negative weights to the associated infohash. Repeated
   failures progressively suppress the torrent in search rankings without
   deleting it from the index.

## Settings tab

The Settings tab contains six sub-tabs for runtime configuration. All changes
write to the SQLite sidecar and take effect on the next request — no process
restart required.

### Configuration

General runtime settings that control dashboard behavior:

- **Dashboard refresh interval** — how often stat cards and the activity feed
  auto-refresh (default: 30 seconds).
- **Default view mode** — poster grid or list view for the Library tab.
- **Items per page** — pagination size for Library, Wants, and Evidence lists.
- **Timezone** — display timezone for all timestamps in the dashboard.
- **Date format** — ISO 8601, US, or European date formatting.

### Auth and Security

Controls for the authentication subsystem:

- **Require authentication** — master toggle (maps to `REQUIRE_AUTH`).
- **API key display** — masked display of the current `DASHBOARD_API_KEY` with
  a reveal toggle and copy button.
- **Key regeneration** — button to generate a new API key. The old key is
  immediately invalidated. Update your *arr indexer configuration with the new
  key after regeneration.
- **Trusted headers** — toggles for `TRUST_NPM_HEADERS` and
  `TRUST_FORWARDED_USER` with inline warnings about the security implications
  of enabling header trust.
- **SSO cookie name** — text field to set or clear `SSO_COOKIE_NAME`.
- **Active sessions** — list of currently authenticated sessions with IP, user
  agent, and last-seen timestamp.

### Integrations

Connection settings for external services:

- **GraphQL endpoint** — displays and allows editing of
  `BITAGENT_GRAPHQL_URL`. Includes a connectivity test button.
- **Metrics endpoint** — displays and allows editing of
  `BITAGENT_METRICS_URL`. Includes a connectivity test button.
- **TMDB API key** — masked input for `TMDB_API_KEY` with a test button that
  fetches a known movie poster to verify the key.
- **Webhook endpoints** — list of configured *arr webhook URLs with
  health-check status indicators.

### Retention

Controls for automatic data lifecycle management:

- **Torrent retention** — TTL in days for indexed torrents without evidence
  (default: 90 days).
- **Evidence retention** — TTL in days for webhook event records (default: 180
  days).
- **Poster cache TTL** — how long TMDB poster URLs are cached before
  re-fetching (default: 7 days).
- **Dry-run toggle** — preview what a retention sweep would delete before
  committing.
- **Manual purge** — button to trigger an immediate retention sweep with
  confirmation dialog.

### Classifier

Tuning controls for the CEL classification pipeline:

- **Classifier batch size** — number of torrents processed per classification
  cycle.
- **Classifier concurrency** — parallel worker count.
- **LLM rerank gate** — toggle to enable or disable the optional LLM
  disambiguation step for low-confidence classifications.
- **Confidence threshold** — minimum confidence score required to accept a
  classification without LLM rerank.
- **Rule chain viewer** — read-only display of the active CEL rules in
  priority order with match statistics.

### Audit Log

A complete, immutable history of every settings change made through the
dashboard:

- **Timestamp** — when the change was made.
- **Actor** — the authenticated identity that made the change (from the auth
  resolver).
- **Key** — which setting was modified.
- **Old value** — the previous value (masked for sensitive fields like API
  keys).
- **New value** — the new value (masked for sensitive fields).

The audit log is append-only and stored in the SQLite sidecar. It cannot be
cleared through the dashboard interface. Export to CSV is available via the
download button in the top-right corner.

## System tab

Diagnostic tools for operators who need to verify connectivity, test endpoints,
and inspect raw data.

### Health checks

A panel displaying the status of every dependency:

- **BitAgent core** — GraphQL endpoint reachability and response time.
- **PostgreSQL** — connection pool status, active queries, and replication lag
  (if applicable).
- **SQLite sidecar** — file integrity check and disk usage.
- **DHT network** — peer count, bootstrap status, and routing table size.
- **TMDB API** — connectivity and rate-limit headroom (if configured).

Each check runs on page load and can be re-triggered individually or all at
once via the **Run All** button.

### Torznab tester

An interactive form for testing Torznab queries without leaving the dashboard:

- **Search type** — dropdown: `search`, `tvsearch`, `movie`, `music`, `book`.
- **Query** — free-text search term.
- **Parameters** — optional fields for season, episode, TVDB ID, IMDB ID.
- **API key** — pre-filled with `TORZNAB_API_KEY` (masked, with reveal
  toggle).

Click **Execute** to send the query and view the raw XML response in a
syntax-highlighted panel. Response time and result count are displayed above
the response body.

### GraphQL explorer

An embedded GraphQL IDE for running arbitrary queries against the BitAgent core:

- **Query editor** — syntax-highlighted textarea with autocomplete for known
  schema types and fields.
- **Variables panel** — JSON editor for query variables.
- **Response panel** — formatted JSON output with collapsible nested objects.
- **History** — recent queries are saved locally and can be re-executed with
  one click.

Common queries are available as presets in a dropdown: `searchTorrents`,
`getReleaseDetails`, `listEvidenceEvents`, `systemHealth`.

### Raw metrics

A passthrough view of the Prometheus metrics exposed by the BitAgent core at
`BITAGENT_METRICS_URL`. Displays the raw `/metrics` output in a monospace,
scrollable panel with a search/filter bar for locating specific metric names.

Useful for operators who need to verify metric exposition without configuring
a full Prometheus + Grafana stack.

## Keyboard shortcuts

The dashboard supports keyboard shortcuts for fast navigation. All shortcuts
work globally unless a text input is focused.

### Tab navigation

| Shortcut | Action |
|---|---|
| `Alt+1` | Switch to Dashboard tab |
| `Alt+2` | Switch to Library tab |
| `Alt+3` | Switch to Wants tab |
| `Alt+4` | Switch to Evidence tab |
| `Alt+5` | Switch to Settings tab |
| `Alt+6` | Switch to System tab |

### Global actions

| Shortcut | Action |
|---|---|
| `Ctrl+K` | Focus the global search bar (works from any tab) |
| `R` | Refresh the current tab's data |
| `Esc` | Close the active modal, dropdown, or sidebar |
| `?` | Show the keyboard shortcuts help overlay |

### Library-specific

| Shortcut | Action |
|---|---|
| `G` | Toggle between grid and list view |
| `Left` / `Right` | Navigate between pages in the torrent list |
| `Enter` | Open the detail modal for the focused torrent |

### Wants-specific

| Shortcut | Action |
|---|---|
| `N` | Open the New Want form |
| `Left` / `Right` | Navigate between pages |

## Theming

The dashboard supports dark and light color modes with automatic detection of
your operating system preference.

### Automatic mode

By default, the dashboard reads the `prefers-color-scheme` media query from
your browser and applies the matching theme on load. If your OS is set to dark
mode, the dashboard renders in dark mode automatically — no manual action
required.

### Manual toggle

A sun/moon icon button in the top-right corner of the navigation bar allows
manual override. Click to cycle between:

1. **Light mode** — white backgrounds, dark text, indigo accents.
2. **Dark mode** — slate backgrounds, light text, indigo accents.
3. **System** — revert to automatic OS preference detection.

The selected preference is persisted in `localStorage` and survives browser
restarts.

### CSS custom properties

The theme system uses CSS custom properties scoped to `[data-theme="light"]`
and `[data-theme="dark"]` selectors. Operators who want to customize colors
beyond the default palette can mount a custom stylesheet at
`/static/custom.css` — the dashboard loads this file if it exists, and
custom properties defined there override the defaults.

Key properties available for override:

- `--color-bg-primary` — main background color
- `--color-bg-secondary` — card and panel background
- `--color-text-primary` — primary text color
- `--color-text-secondary` — secondary/muted text color
- `--color-accent` — accent color for links, buttons, and active states
- `--color-success` — green status indicators
- `--color-warning` — yellow status indicators
- `--color-danger` — red status indicators and error states
