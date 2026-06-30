# GitHub Star Atlas

A readable, auto-refreshing atlas of every public GitHub repository with more than **10,000 stars**.

This repository is being bootstrapped automatically from the live Agent37 build. The bootstrap workflow downloads the prepared source archive, commits the full Vite app, data fetchers, docs, and 12-hour refresh workflow, then the normal refresh workflow keeps `public/data.json` updated.

Live preview: https://exposed-port-8140-0f61795f7a08cb00c92b-vh6v7rj2oe.h68.openclaw.agent37.com/

After bootstrap completes, this repo will include:

- exhaustive GitHub 10k+ star crawler
- GitHub Trending merger
- Crunchbase-style readable data table
- rows-per-page selector
- competitive comparison docs
- GitHub Actions refresh every 12 hours

