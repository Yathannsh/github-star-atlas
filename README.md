# GitHub Star Atlas

A readable, auto-refreshing atlas of every public GitHub repository with more than **10,000 stars**.

Unlike a simple leaderboard, GitHub Star Atlas combines lifetime popularity with momentum signals from GitHub Trending and lightweight hot-ranking models inspired by Reddit and Hacker News.

## Why this exists

Most GitHub discovery tools optimize for one lens:

- GitHub Trending: what is hot right now, but not exhaustive.
- Gitstar Ranking: lifetime-star rankings, but low trend context.
- Star History: excellent charts for selected repos, but not discovery-table first.
- OSS Insight: very powerful event analytics, but heavier and broader than a forkable static atlas.

GitHub Star Atlas focuses on the missing middle: **a fast, legible, forkable table for scanning the high-star open-source universe and spotting what is moving now.**

See [`docs/comparison.md`](docs/comparison.md) for the full competitive comparison.

## Features

- **Exhaustive 10k+ repo dataset** using recursive star-count partitioning to bypass GitHub's 1,000-result search window.
- **Readable Crunchbase-style table** with a dedicated two-line description column.
- **Rows-per-page selector**: 25, 50, 100, 250, 500, or all rows.
- **Momentum tab** with GitHub Trending daily / weekly / monthly signals.
- **Transparent scoring** via hot, velocity, and gravity-style sorting.
- **Filters** for search, language, trend window, activity, license, and sort order.
- **Downloadable JSON snapshot** at `/data.json`.
- **Automatic refresh every 12 hours** via GitHub Actions.
- **Static Vite app** that can be hosted on GitHub Pages, Vercel, Netlify, Cloudflare Pages, or any static host.

## Current snapshot

- Repositories: **5,340**
- Threshold: **>10,000 stars**
- Trend sources: GitHub Trending daily / weekly / monthly
- Dataset file: [`public/data.json`](public/data.json)

## Screens and ranking modes

### Leaderboard

Lifetime-star-first view of the complete 10k+ universe. Best for broad scanning and filtering.

### What's up

Momentum-first view. It promotes repositories with current GitHub Trending signals and fresh activity rather than only lifetime stars.

### Method

Explains the data collection approach, GitHub Search API limitations, and the ranking lenses used by the UI.

## Data collection

```bash
python3 fetch_github_10k.py   # exhaustive 10k+ crawl
python3 fetch_trending.py     # merge GitHub Trending signals
```

The 10k+ crawl recursively splits the search into non-overlapping star ranges so each GitHub Search API query stays under the 1,000-result result-window cap. Repositories are de-duplicated and ranked after the crawl.

## Development

```bash
npm install
npm run dev -- --port 8140 --host 0.0.0.0
```

## Build

```bash
npm run build
```

## Auto-refresh

The included GitHub Actions workflow runs every 12 hours:

```yaml
schedule:
  - cron: '0 */12 * * *'
```

It refreshes `public/data.json`, rebuilds the app, and commits the updated data if the snapshot changed.

## Repository structure

```text
.github/workflows/refresh.yml   # 12-hour data refresh
public/data.json                 # generated dataset snapshot
src/main.js                      # client app and ranking logic
src/style.css                    # data-table UI system
fetch_github_10k.py              # exhaustive GitHub Search API crawler
fetch_trending.py                # GitHub Trending scraper/merger
docs/comparison.md               # competitive comparison and product gaps
```

## Notes

- GitHub star counts change constantly, so exact counts drift between refreshes.
- GitHub Trending is a rolling ranking; daily / weekly / monthly positions can shift during a day.
- For unauthenticated local runs, GitHub Search API rate limits make the crawl slower. In GitHub Actions, the workflow uses `github.token`.

## License

MIT
