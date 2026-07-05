# Historical crossing dates for all repos + extended descriptions

Date: 2026-07-05
Status: Approved

## Goal

1. Every repository carries the date it first crossed 10,000 stars — including
   the ~5,352 founding members — so the Arrivals tab lists the entire universe
   sortable by date (newest and oldest first).
2. Every repository gets an extended description (what it actually does),
   extracted from its README, shown when a row is expanded.

## Method

### Crossing dates (historical reconstruction)

The GitHub stargazers API with `Accept: application/vnd.github.star+json`
returns `starred_at` per star, oldest first. The 10,000th star is the last
item of page 100 at `per_page=100` — one request per repo gives the date it
crossed the threshold. Caveats (acceptable, documented in Method tab):
unstars and deleted accounts shift the estimate slightly; repos currently
below 10,001 stars may return a short page and stay undated.

Constraint discovered: OAuth tokens (gh CLI) 404 on this endpoint for org
repos; unauthenticated is capped at 60 req/h. GitHub Actions' GITHUB_TOKEN
(GitHub App token, 1,000 req/h/repo) works — so the date backfill runs in CI:
`backfill.yml` on an hourly cron, each run spending ~900 requests, committing
progress to `public/first_seen.json`, no-op once complete (~6 runs total).
Existing non-null registry dates (live-tracked crossers) are never
overwritten.

### Extended descriptions

Fetched from `raw.githubusercontent.com/{repo}/{default_branch}/README*`
(no API, no rate limit) and reduced to readable prose: strip code blocks,
HTML, badges, links, tables, headings; keep the first paragraphs up to ~700
chars. Stored in `public/details.json` keyed by repo id; lazy-loaded by the
UI on first row expansion (~1MB gzipped, not part of initial page load).
Runs locally once for all repos; the refresh workflow tops up new arrivals.

### Ongoing accuracy

`fetch_github_10k.py` now dates brand-new crossers via the same
stargazers lookup at refresh time (exact date) with "today" as fallback.
`refresh.yml` also runs a details top-up and commits `details.json`.

## UI

- Row click expands an inline detail panel under the row (all tabs): full
  metadata plus the extended "About" section (README extract, falling back to
  the GitHub description). Click again to collapse.
- Arrivals tab: sort gains "Oldest first" (`arrived_asc`); repos without a
  reconstructed date yet are excluded until the backfill dates them.
- Undated repos sort last under both date sorts.

## Testing

Script logic on a small `--limit` sample locally (dates unauthenticated,
details via raw); UI verified in the browser with partial details data;
full date backfill validated by watching the first backfill.yml run.
