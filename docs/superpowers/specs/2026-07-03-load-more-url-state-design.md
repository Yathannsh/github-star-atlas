# Load-more reading flow + URL-synced views

Date: 2026-07-03
Status: Approved

## Goal

Let a visitor read the repo list as one continuous list: when they reach the end
of what is shown, they can reveal the next batch in place instead of flipping
pages. Also make every sorted/filtered view shareable via the URL instead of
building separate pages per sort mode.

## Decisions

- **Hybrid load-more**: a "Show N more" button appends the next batch below the
  rows already read. After the first click (explicit intent), an
  IntersectionObserver auto-appends further batches as the reader nears the
  bottom. A "↑ Top" button is always available at the list foot.
- **URL state, no routes**: `tab`, `sort`, `q`, `language`, `license`,
  `activity`, `trend` sync to query params via `history.replaceState`.
  Defaults are omitted so the base URL stays clean. State is restored from the
  URL on load.
- **No separate pages for sort modes**: tabs + sort dropdown + shareable URLs
  cover the need; dedicated routes would duplicate the table.

## Behavior details

- `state.page` and the prev/next pager are removed; `state.visibleCount`
  (initialized to the batch size) replaces them.
- The "Rows" selector becomes "Batch" and controls batch size
  (25/50/100/250/500/All). "All" renders everything with no load button.
- Appending inserts row HTML into the existing table (no full re-render), so
  scroll position is untouched.
- Any tab/filter/sort/batch change resets `visibleCount` to one batch and turns
  auto-load off (fresh reading session).
- Table meta shows "N of M shown" instead of "page X / Y".
- Empty-state message unchanged.

## Testing

Manual browser verification at desktop and narrow widths: load-more appends
without scroll jump; auto-load engages only after the first click; filter
changes reset the list; a pasted URL with params restores the same view.
