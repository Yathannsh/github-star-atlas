#!/usr/bin/env python3
"""Backfill historical 10k-crossing dates and extended descriptions.

--dates    For registry entries without a date, fetch the timestamp of the
           repo's 10,000th star (last item of stargazers page 100 at
           per_page=100) and write it to public/first_seen.json. Needs a
           token that can read org stargazers (GitHub Actions GITHUB_TOKEN
           works; gh CLI OAuth tokens 404 on org repos).
--details  For repos missing from public/details.json, fetch the README via
           raw.githubusercontent.com and extract readable prose.

Both modes checkpoint continuously and are safe to re-run until done.
"""
import argparse
import json
import re
import sys
import time
import os
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "public" / "data.json"
FIRST_SEEN = ROOT / "public" / "first_seen.json"
DETAILS = ROOT / "public" / "details.json"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
API_HEADERS = {
    "Accept": "application/vnd.github.star+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "github-star-atlas backfill",
}
if TOKEN:
    API_HEADERS["Authorization"] = f"Bearer {TOKEN}"

MIN_RATE_HEADROOM = 20
CROSSING_PAGE = 100  # per_page=100 -> last item of page 100 is star #10,000
DESC_TARGET_CHARS = 700
DESC_MIN_CHARS = 40


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return default


def save_registry(registry: dict) -> None:
    FIRST_SEEN.write_text(json.dumps(registry, sort_keys=True, indent=1), encoding="utf-8")


def save_details(details: dict) -> None:
    DETAILS.write_text(json.dumps(details, sort_keys=True, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def crossing_date(full_name: str) -> tuple[str | None, int]:
    """Return (ISO date of the 10,000th star or None, remaining rate)."""
    url = (f"https://api.github.com/repos/{full_name}/stargazers"
           f"?per_page=100&page={CROSSING_PAGE}")
    req = urllib.request.Request(url, headers=API_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            remaining = int(resp.headers.get("x-ratelimit-remaining", "1"))
            items = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        remaining = int(e.headers.get("x-ratelimit-remaining", "1") or "1")
        if e.code in (403, 429):
            return None, 0  # rate limited; caller stops
        return None, remaining  # 404/451/...: leave undated
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None, 1
    if isinstance(items, list) and len(items) == 100:
        starred = items[-1].get("starred_at")
        if starred:
            return starred[:10], remaining
    return None, remaining


README_CANDIDATES = ["README.md", "readme.md", "Readme.md", "README.MD",
                     "README.rst", "README", "readme", "README.markdown"]


def fetch_readme(full_name: str, branch: str) -> str | None:
    for name in README_CANDIDATES:
        url = f"https://raw.githubusercontent.com/{full_name}/{branch}/{name}"
        req = urllib.request.Request(url, headers={"User-Agent": API_HEADERS["User-Agent"]})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read(65536).decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            continue
    return None


BADGE_RE = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
TAG_RE = re.compile(r"<[^>]+>")
CODEBLOCK_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def extract_description(markdown: str) -> str | None:
    """Reduce a README to its first readable prose paragraphs."""
    text = COMMENT_RE.sub("", CODEBLOCK_RE.sub("", markdown))
    text = BADGE_RE.sub("", text)
    text = LINK_RE.sub(r"\1", text)
    text = TAG_RE.sub(" ", text)
    paragraphs, current = [], []
    for raw in text.splitlines():
        line = raw.strip()
        is_noise = (not line or line.startswith(("#", "|", ">", "---", "===", "***", "- [", "* ["))
                    or set(line) <= {"-", "=", "*", " "}
                    or "shields.io" in line or "img.shields" in line)
        if is_noise:
            if current:
                paragraphs.append(" ".join(current)); current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    out = []
    total = 0
    for p in paragraphs:
        p = re.sub(r"\s+", " ", p).replace("**", "").replace("__", "").replace("`", "").strip()
        if len(p) < 25:  # skip stubs like license one-liners
            continue
        out.append(p)
        total += len(p)
        if total >= DESC_TARGET_CHARS:
            break
    result = "\n\n".join(out)[: DESC_TARGET_CHARS + 300].strip()
    return result if len(result) >= DESC_MIN_CHARS else None


def run_dates(repos: list[dict], budget: int) -> None:
    registry = load_json(FIRST_SEEN, {})
    by_id = {str(r["id"]): r for r in repos}
    pending = [k for k, v in registry.items() if v is None and k in by_id]
    print(f"dates: {len(pending)} repos undated, budget {budget}", flush=True)
    done = 0
    for key in pending:
        if done >= budget:
            break
        date, remaining = crossing_date(by_id[key]["full_name"])
        done += 1
        if date:
            registry[key] = date
        if remaining <= MIN_RATE_HEADROOM:
            print("rate limit headroom exhausted; stopping", flush=True)
            break
        if done % 50 == 0:
            save_registry(registry)
            print(f"  {done} looked up, {sum(1 for v in registry.values() if v)} dated total", flush=True)
    save_registry(registry)
    left = sum(1 for k, v in registry.items() if v is None and k in by_id)
    print(f"dates: pass complete, {left} still undated", flush=True)


def run_details(repos: list[dict], budget: int, workers: int = 8) -> None:
    details = load_json(DETAILS, {})
    pending = [r for r in repos if str(r["id"]) not in details][:budget]
    print(f"details: {len(pending)} repos missing descriptions", flush=True)

    def work(repo):
        md = fetch_readme(repo["full_name"], repo.get("default_branch") or "master")
        return str(repo["id"]), (extract_description(md) if md else None)

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, r) for r in pending]
        for fut in as_completed(futures):
            key, desc = fut.result()
            details[key] = desc or ""  # empty string = tried, nothing usable
            done += 1
            if done % 200 == 0:
                save_details(details)
                print(f"  {done}/{len(pending)} fetched", flush=True)
    save_details(details)
    usable = sum(1 for v in details.values() if v)
    print(f"details: pass complete, {usable}/{len(details)} usable descriptions", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", action="store_true")
    ap.add_argument("--details", action="store_true")
    ap.add_argument("--budget", type=int, default=900)
    args = ap.parse_args()
    if not (args.dates or args.details):
        ap.error("pass --dates and/or --details")
    data = load_json(DATA, None)
    if not data:
        sys.exit("public/data.json missing")
    repos = data["repos"]
    if args.dates:
        run_dates(repos, args.budget)
    if args.details:
        run_details(repos, args.budget)


if __name__ == "__main__":
    main()
