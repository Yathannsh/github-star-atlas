# Arrivals page + return to classic pagination

Date: 2026-07-03
Status: Approved

## Change of direction

User feedback after testing: no infinite scroll / auto-load — "just do a
hundred a page kind of deal." This supersedes the hybrid load-more design in
2026-07-03-load-more-url-state-design.md. URL state and the reset-on-filter
behavior are kept.

## Design

### Classic pagination (all table tabs)

- `state.page` returns; `visibleCount`/`autoLoad`/IntersectionObserver and the
  load-more foot are removed.
- Rows selector (back to "Rows", default 100) controls page size.
- Top of table: "Page X of Y" plus compact prev/next arrows.
- Bottom of table: numbered pager (1 … current±2 … last) shown when there is
  more than one page. Page changes scroll back to the top.
- `page` joins the URL params (omitted when 1), so page 3 of a sorted view is
  shareable.

### Arrivals tab

- New tab between What's up and Method listing only repos with a non-null
  `first_seen`, default sort "Newest first" (`arrived`).
- Last table column shows the crossing date ("Crossed 10k") instead of trend
  pills; other columns unchanged.
- Empty state (true until refreshes accumulate dated crossers): explains that
  tracking just began and new 10k-crossers appear after each refresh.
- Founding members (pre-tracking, `first_seen: null`) are deliberately absent.

## Testing

Browser verification against stamped test data: arrivals tab lists only dated
repos newest-first with date column; leaderboard paginates 100/page with
working numbered pager; `?page=N` round-trips; filters reset to page 1;
scrolling never auto-appends; banner flow still works.
