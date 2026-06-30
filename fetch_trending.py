#!/usr/bin/env python3
"""Scrape GitHub Trending (daily/weekly/monthly) and merge trend signals into public/data.json."""
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "public" / "data.json"
UA = "Mozilla/5.0 (compatible; Hermes-Agent37 GitHub Star Atlas)"

class TrendingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_article = False
        self.depth = 0
        self.current = None
        self.in_h2 = False
        self.in_p = False
        self.in_link = False
        self.link_href = ""
        self.textbuf = []
        self.repos = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "")
        if tag == "article" and "Box-row" in classes:
            self.in_article = True
            self.depth = 1
            self.current = {"full_name": "", "description": "", "language": None, "stars": None, "forks": None, "stars_gained": None, "url": None}
        elif self.in_article:
            self.depth += 1
            if tag == "h2":
                self.in_h2 = True; self.textbuf = []
            elif tag == "p" and "col-9" in classes:
                self.in_p = True; self.textbuf = []
            elif tag == "a" and self.in_h2:
                self.in_link = True; self.link_href = attrs.get("href", "")

    def handle_endtag(self, tag):
        if self.in_article:
            if tag == "h2" and self.in_h2:
                name = re.sub(r"\s+", "", "".join(self.textbuf)).strip()
                self.current["full_name"] = name
                self.current["url"] = "https://github.com/" + name
                self.in_h2 = False
                self.in_link = False
                self.textbuf = []
            elif tag == "p" and self.in_p:
                self.current["description"] = re.sub(r"\s+", " ", "".join(self.textbuf)).strip()
                self.in_p = False
                self.textbuf = []
            if tag == "article":
                self.repos.append(self.current)
                self.in_article = False
                self.current = None
            else:
                self.depth -= 1

    def handle_data(self, data):
        if not self.in_article:
            return
        text = data.strip()
        if not text:
            return
        if self.in_h2 or self.in_p:
            self.textbuf.append(data)
        if self.current is None:
            return
        # GitHub's trending row text has language, total stars, forks, and period stars.
        if re.match(r"^[\d,]+ stars? (today|this week|this month)$", text):
            self.current["stars_gained"] = int(re.sub(r"\D", "", text))
        elif re.match(r"^[\d,]+$", text):
            n = int(text.replace(",", ""))
            if self.current["stars"] is None:
                self.current["stars"] = n
            elif self.current["forks"] is None:
                self.current["forks"] = n
        elif self.current.get("language") is None and not any(x in text.lower() for x in ["built by", "stars today", "stars this"]):
            # Heuristic: language is a short text node between color dot and star/fork counts.
            if len(text) < 32 and "/" not in text and "\n" not in text and not text.startswith("Sponsor"):
                self.current["language"] = text

def fetch_period(period):
    url = f"https://github.com/trending?since={period}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        html = resp.read().decode("utf-8", "replace")
    parser = TrendingParser(); parser.feed(html)
    rows = []
    for idx, r in enumerate(parser.repos, 1):
        if r.get("full_name"):
            r["rank"] = idx
            r["period"] = period
            rows.append(r)
    return rows

def main():
    data = json.loads(DATA_PATH.read_text())
    repos_by_name = {r["full_name"].lower(): r for r in data["repos"]}
    trending = {}
    for period in ["daily", "weekly", "monthly"]:
        rows = fetch_period(period)
        trending[period] = rows
        for row in rows:
            repo = repos_by_name.get(row["full_name"].lower())
            if not repo:
                continue
            repo.setdefault("trending", {})[period] = {
                "rank": row["rank"],
                "stars_gained": row.get("stars_gained"),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
    data["trending_snapshot"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://github.com/trending",
        "periods": {k: len(v) for k, v in trending.items()},
        "rows": trending,
        "note": "GitHub Trending is a rolling ranking based on recent popularity, exposed here as daily/weekly/monthly lists with period star gains when GitHub renders them.",
    }
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("merged trending:", {k: len(v) for k, v in trending.items()})
    print("matched 10k+ repos:", sum(1 for r in data["repos"] if r.get("trending")))

if __name__ == "__main__":
    main()
