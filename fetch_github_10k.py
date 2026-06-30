#!/usr/bin/env python3
"""Fetch all public GitHub repositories with >10,000 stars.

Uses GitHub Search API and recursively partitions by star count because GitHub only
returns the first 1,000 results for any single search query. The script respects
search rate limits and writes public/data.json for the website.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "public" / "data.json"
USER_AGENT = "Hermes-Agent37 github-stars-10k-site"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": USER_AGENT,
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

last_search_at = 0.0

def request_json(url: str, *, search: bool = True):
    global last_search_at
    # Unauthenticated GitHub search is 10 req/min. Keep a conservative spacing.
    if search and not TOKEN:
        elapsed = time.time() - last_search_at
        if elapsed < 6.3:
            time.sleep(6.3 - elapsed)
    while True:
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                last_search_at = time.time() if search else last_search_at
                return json.loads(body), resp.headers
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            remaining = e.headers.get("x-ratelimit-remaining")
            reset = e.headers.get("x-ratelimit-reset")
            if e.code in (403, 429) and remaining == "0" and reset:
                wait = max(1, int(reset) - int(time.time()) + 2)
                print(f"Rate limited; sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"GitHub API error {e.code}: {body[:500]} for {url}")

def search_count(query: str) -> int:
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({
        "q": query,
        "per_page": 1,
    })
    data, _ = request_json(url)
    return int(data["total_count"])

def search_page(query: str, page: int, per_page: int = 100):
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
        "page": page,
    })
    data, headers = request_json(url)
    return data["items"], headers

def query_for(lo: int, hi: int | None) -> str:
    if hi is None:
        return f"stars:>{lo}"
    if lo == hi:
        return f"stars:{lo}"
    return f"stars:{lo}..{hi}"

def partition(lo: int, hi: int | None, depth=0):
    q = query_for(lo, hi)
    count = search_count(q)
    print(f"{'  '*depth}{q}: {count}", flush=True)
    if count <= 1000:
        return [(lo, hi, count)]
    if hi is None:
        # Find max-ish upper bound by probing the current top repo once.
        items, _ = search_page(q, 1, 1)
        max_star = int(items[0]["stargazers_count"])
        hi = max_star
        count = search_count(query_for(lo, hi))
        print(f"{'  '*depth}bounded to {query_for(lo, hi)}: {count}", flush=True)
        if count <= 1000:
            return [(lo, hi, count)]
    if hi <= lo:
        return [(lo, hi, count)]
    mid = (lo + hi) // 2
    # Fetch high ranges first for better progressive UI if interrupted.
    return partition(mid + 1, hi, depth + 1) + partition(lo, mid, depth + 1)

def compact_repo(r):
    return {
        "id": r["id"],
        "rank": None,
        "name": r["name"],
        "full_name": r["full_name"],
        "owner": r["owner"]["login"],
        "owner_avatar": r["owner"].get("avatar_url"),
        "html_url": r["html_url"],
        "description": r.get("description"),
        "language": r.get("language"),
        "stars": r.get("stargazers_count", 0),
        "forks": r.get("forks_count", 0),
        "open_issues": r.get("open_issues_count", 0),
        "watchers": r.get("watchers_count", 0),
        "license": (r.get("license") or {}).get("spdx_id"),
        "topics": r.get("topics") or [],
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
        "pushed_at": r.get("pushed_at"),
        "homepage": r.get("homepage"),
        "archived": r.get("archived", False),
        "disabled": r.get("disabled", False),
        "size": r.get("size"),
        "default_branch": r.get("default_branch"),
    }

def main():
    (ROOT / "public").mkdir(exist_ok=True)
    ranges = partition(10000, None)
    repos = {}
    ranges_out = []
    total_expected = 0
    for lo, hi, count in ranges:
        q = query_for(lo, hi)
        total_expected += count
        pages = math.ceil(count / 100)
        got = 0
        print(f"Fetching {q}: {count} repos across {pages} pages", flush=True)
        for page in range(1, pages + 1):
            items, headers = search_page(q, page, 100)
            for item in items:
                if item.get("stargazers_count", 0) > 10000:
                    repos[item["full_name"].lower()] = compact_repo(item)
            got += len(items)
            print(f"  page {page}/{pages}: {len(items)} items (search remaining {headers.get('x-ratelimit-remaining')})", flush=True)
        ranges_out.append({"query": q, "lo": lo, "hi": hi, "github_count": count, "fetched": got})
    # Star counts can change while the crawl is running. Reconcile the live top
    # window so a repo that moved above our initial upper bound is not missed.
    top_query = f"stars:>{max((r['stars'] for r in repos.values()), default=10000)}"
    top_added = []
    top_count = 0
    try:
        top_items, _ = search_page(top_query, 1, 100)
        top_count = len(top_items)
        for item in top_items:
            if item.get("stargazers_count", 0) > 10000:
                key = item["full_name"].lower()
                if key not in repos:
                    top_added.append(item["full_name"])
                repos[key] = compact_repo(item)
    except Exception as exc:
        print(f"Top-window reconciliation failed: {exc}", file=sys.stderr)

    repo_list = sorted(repos.values(), key=lambda r: (-r["stars"], r["full_name"].lower()))
    for i, r in enumerate(repo_list, 1):
        r["rank"] = i
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": 10000,
        "source": "GitHub Search API",
        "method": "Recursive star-count partitioning to bypass GitHub's 1,000-result search window per query, followed by a live top-window reconciliation for repos whose stars changed during the crawl.",
        "expected_from_range_counts": total_expected,
        "top_reconciliation": {"query": top_query, "fetched": top_count, "added": top_added},
        "count": len(repo_list),
        "ranges": ranges_out,
        "repos": repo_list,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} with {len(repo_list)} unique repositories; expected count sum {total_expected}")

if __name__ == "__main__":
    main()
