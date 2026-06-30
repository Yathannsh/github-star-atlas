# Competitive landscape

GitHub Star Atlas is a deliberately opinionated, exhaustive, readable atlas of public GitHub repositories with more than 10,000 stars. It combines a full lifetime-star universe with short-window momentum signals.

## Compared tools

| Tool | What it is good at | Gap this project targets |
|---|---|---|
| GitHub Trending | Official daily / weekly / monthly discovery by language. Excellent for what is hot *right now*. | It is a rolling top list, not an exhaustive ranked atlas. It does not show the full 10k+ universe, long-tail filters, or a persistent dataset snapshot. |
| Gitstar Ranking | Simple lifetime-star leaderboard for top users, organizations, and repositories. | Mostly lifetime stars. Limited trend context, fewer discovery lenses, and less data-table ergonomics for scanning descriptions. |
| OSS Insight | Deep GitHub event analytics, rankings, historical trends, and natural-language insights over billions of events. | Powerful but broad. This project is lighter: a static, forkable, transparent dataset and UI focused specifically on high-star repositories and momentum explainability. |
| Star History | Best-in-class charting for star history comparisons between selected repositories. | It is comparison-chart first, not exhaustive discovery-table first. This project helps decide what to inspect before charting individual repos. |
| Trendshift / similar trending trackers | Live rising-repository detection and discovery. | Usually not an exhaustive 10k+ atlas and may emphasize current movers without the lifetime context. |
| Crunchbase / Airtable-style data products | Excellent master-list ergonomics: saved views, configurable rows, dense columns, row actions, and detail views. | They are not GitHub-native open-source discovery datasets. This project borrows their table readability and applies it to GitHub repositories. |

## Differentiators

1. **Exhaustive threshold dataset** — fetches every public repo above 10k stars using star-range partitioning instead of relying on GitHub's 1,000-result search window.
2. **Readable data-table first** — dedicated description column, row-count selector, compact/comfort density, and stable scan columns.
3. **Momentum + lifetime together** — lifetime stars sit beside GitHub Trending daily/weekly/monthly signals.
4. **Transparent scoring** — the Method tab explains GitHub Trending, Reddit-style hot, and HN-style gravity scoring instead of hiding a black-box rank.
5. **Static and forkable** — the whole site is a Vite static app with JSON data, so it can be hosted anywhere and inspected easily.
6. **Auto-refreshable** — GitHub Actions schedule refreshes the dataset every 12 hours and commits the updated snapshot.

## Features intentionally built from gaps

- **Rows per page selector** because large datasets need user-controlled density.
- **Description-first table layout** because many GitHub ranking pages bury the description or truncate it too aggressively.
- **What’s up tab** because lifetime star rankings are stable but do not reveal current shifts.
- **Downloadable JSON** because the dataset itself should be useful for researchers and builders.
- **Methodology docs** because star rankings are easy to misinterpret without knowing GitHub Search API limits and trending-window limitations.

## Future opportunities

- Historical snapshots with true 12h star deltas, not just current GitHub Trending period gains.
- Saved views encoded in URL params.
- Compare selected repositories with mini sparklines.
- Topic clustering and semantic search.
- Maintainer-health signals: recent issues, PR merge activity, release cadence, archival state.
