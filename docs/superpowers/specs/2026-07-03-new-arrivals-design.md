# New arrivals: first_seen tracking, NEW lens, last-visit banner

Date: 2026-07-03
Status: Approved

## Problem

The dataset refreshes every 12 hours and new repositories cross the 10,000-star
threshold, but they are spliced invisibly into rank order. A reader who has
already been through the list has no way to answer "what's new since I was
here?" and will not re-read 5,000 entries.

## Design

### A. Pipeline: `first_seen` registry (foundation)

- `public/first_seen.json` is an append-only registry mapping repo id →
  ISO date the repo was first observed above 10k stars (or `null` for
  founding members present when tracking began).
- `fetch_github_10k.py` loads the registry, stamps every crawled repo's
  `first_seen` from it, adds unseen ids with today's UTC date, and writes the
  registry back. Ids are never restamped and never removed, so a repo that
  hovers around the threshold keeps its earliest crossing date.
- If the registry is missing entirely (first run), all current repos are
  founding members (`null`) — 5,300 repos must not all claim to be new.
- A founding registry generated from the current `data.json` is committed with
  this change.
- `refresh.yml` commits `public/first_seen.json` alongside `public/data.json`.

### B. UI: "new arrivals" lens (for everyone)

- A green "New" pill on rows whose `first_seen` is within 14 days.
- A "New arrivals" sort (newest `first_seen` first, founding members last,
  stars as tie-breaker) on both table tabs, valid in the URL (`?sort=arrived`).
- Trend filter gains "New this week" and "New this month" options.

### C. UI: "since your last visit" banner (per user)

- localStorage keys `visitPrevious` / `visitCurrent`; a visit more than 1 hour
  after `visitCurrent` rolls it into `visitPrevious`, so reloads within a
  session keep the same reference point.
- On table tabs, when repos have `first_seen` on or after the day of the
  previous visit, show a banner: "N repos crossed 10k since your last visit"
  with "Show them" (filters to just those, toggles to "Show all") and a
  dismiss button (session-scoped, not persisted).
- Day granularity: comparison uses the UTC date of the previous visit, which
  can over-count same-day arrivals; the banner is dismissible so this is
  acceptable.
- Not URL-synced — it is per-user state, not a shareable view.

### Out of scope (parked)

RSS/Atom arrivals feed; changelog tab backed by per-refresh history.

## Testing

- Registry merge logic exercised with fixture files (fresh registry, carry
  forward, new arrival, dropped repo retained).
- UI verified in the browser against a locally stamped copy of `data.json`
  (restored afterwards): pills, sort order, week/month filters, banner count,
  show-them toggle, dismiss.
