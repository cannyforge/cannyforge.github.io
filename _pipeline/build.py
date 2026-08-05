#!/usr/bin/env python3
"""Regenerate derived content from the site's sources of truth.

Run from the repo root after editing manifest.json or anything in _partials/:

    python3 _pipeline/build.py            # write
    python3 _pipeline/build.py --check    # verify only, non-zero exit if stale

Two jobs:

1. **Partial sync.** Blocks that appear on more than one page (analytics tag,
   email capture, site header, giscus) live once in `_partials/`. Any page can
   opt in by wrapping the block in `<!-- BEGIN:name -->` / `<!-- END:name -->`,
   where `name` matches the partial's filename. Pages without a given marker are
   left alone, so Tier 2 pages can take a different variant (`-tier2`) and
   bespoke pages can opt out entirely.

   This exists because `_templates/` are copy-from templates, not render-through
   layouts: a fix there never reaches published articles. That is how a literal
   `BUTTONDOWN_USERNAME` survived on 10 articles, and a `SITE.goatcounter.com`
   placeholder on another.

2. **Homepage + sitemap.** The article list is baked into index.html so crawlers
   see the articles rather than "Loading...", and sitemap.xml is generated from
   manifest.json so it cannot drift.

Everything is idempotent — running twice produces byte-identical output.
"""

from __future__ import annotations

import sys
import json
import re
from datetime import date, datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTIALS_DIR = ROOT / "_partials"
BASE_URL = "https://cannyforge.dev"
STATIC_PAGES = ["/", "/about.html"]


# ── shared ──────────────────────────────────────────────────────────────────

def target_files() -> list[Path]:
    """Every page that may carry partial markers."""
    files = sorted(ROOT.glob("*/index.html"))
    files = [f for f in files if f.parent.name not in {"_partials", "_pipeline"}]
    files += sorted(ROOT.glob("_templates/*.html"))
    files += [ROOT / n for n in ("index.html", "about.html", "404.html")]
    return [f for f in files if f.exists()]


def replace_block(text: str, name: str, body: str) -> str:
    """Swap the content between <!-- BEGIN:name --> and <!-- END:name -->.

    Indentation is taken from the BEGIN marker and applied to every line of the
    body, so regenerated blocks sit correctly wherever they are used and diffs
    stay quiet.
    """
    pattern = re.compile(
        rf"([ \t]*)<!-- BEGIN:{re.escape(name)} -->.*?<!-- END:{re.escape(name)} -->",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise KeyError(name)
    indent = match.group(1)
    inner = "\n".join(
        (indent + line if line.strip() else line) for line in body.split("\n")
    )
    replacement = f"{indent}<!-- BEGIN:{name} -->\n{inner}\n{indent}<!-- END:{name} -->"
    return pattern.sub(lambda _: replacement, text)


# ── job 1: partial sync ─────────────────────────────────────────────────────

def load_partials() -> dict[str, str]:
    if not PARTIALS_DIR.is_dir():
        return {}
    return {
        p.stem: p.read_text(encoding="utf-8").rstrip("\n")
        for p in sorted(PARTIALS_DIR.glob("*.html"))
    }


def sync_partials(write: bool) -> list[str]:
    """Push every partial into every page that opted in. Returns stale paths."""
    partials = load_partials()
    stale: list[str] = []
    applied = 0
    for path in target_files():
        original = path.read_text(encoding="utf-8")
        text = original
        for name, body in partials.items():
            try:
                text = replace_block(text, name, body)
            except KeyError:
                continue  # page did not opt in to this partial
            applied += 1
        if text != original:
            stale.append(str(path.relative_to(ROOT)))
            if write:
                path.write_text(text, encoding="utf-8")
    print(f"partials      {len(partials)} partial(s), {applied} insertion(s) across "
          f"{len(target_files())} page(s)")
    return stale


# ── job 2: homepage + sitemap ───────────────────────────────────────────────

def load_manifest() -> list[dict]:
    articles = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


def render_chips(articles: list[dict]) -> str:
    seen: list[str] = []
    for a in articles:
        if a["category"] not in seen:
            seen.append(a["category"])
    return "\n".join(
        f'<button class="chip" data-category="{escape(c, quote=True)}">{escape(c)}</button>'
        for c in seen
    )


def render_articles(articles: list[dict]) -> str:
    out = []
    for a in articles:
        out.append(
            f'<a href="/{escape(a["slug"], quote=True)}/" class="article-item" '
            f'data-category="{escape(a["category"], quote=True)}">\n'
            f'  <div class="meta">\n'
            f'    <time datetime="{escape(a["date"], quote=True)}">{escape(a["date"])}</time>\n'
            f'    <span class="category-badge">{escape(a["category"])}</span>\n'
            f'  </div>\n'
            f'  <h2>{escape(a["title"])}</h2>\n'
            f'  <p>{escape(a["description"])}</p>\n'
            f'</a>'
        )
    return "\n".join(out)


def build_index(articles: list[dict], write: bool) -> list[str]:
    path = ROOT / "index.html"
    original = path.read_text(encoding="utf-8")
    text = replace_block(original, "filters", render_chips(articles))
    text = replace_block(text, "articles", render_articles(articles))
    print(f"index.html    {len(articles)} articles baked in")
    if text == original:
        return []
    if write:
        path.write_text(text, encoding="utf-8")
    return ["index.html"]


def build_sitemap(articles: list[dict], write: bool) -> list[str]:
    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc in STATIC_PAGES:
        lines.append(f"  <url>\n    <loc>{BASE_URL}{loc}</loc>\n"
                     f"    <lastmod>{today}</lastmod>\n  </url>")
    for a in articles:
        lines.append(f"  <url>\n    <loc>{BASE_URL}/{a['slug']}/</loc>\n"
                     f"    <lastmod>{a['date']}</lastmod>\n  </url>")
    lines.append("</urlset>")
    body = "\n".join(lines) + "\n"
    path = ROOT / "sitemap.xml"
    print(f"sitemap.xml   {len(articles) + len(STATIC_PAGES)} urls")
    # lastmod on static pages is today's date, so ignore it when checking staleness
    if path.exists() and _ignore_dates(path.read_text(encoding="utf-8")) == _ignore_dates(body):
        return []
    if write:
        path.write_text(body, encoding="utf-8")
    return ["sitemap.xml"]


def _ignore_dates(s: str) -> str:
    return re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", "<lastmod/>", s)


FEED_CHANNEL = {
    "title": "CannyForge",
    "link": BASE_URL,
    "description": ("AI systems engineering — architecture, agent reliability, "
                    "LLM economics, and observations from building."),
    "language": "en-us",
}


def build_feed(articles: list[dict], write: bool) -> list[str]:
    """Generate feed.xml from manifest.json.

    Hand-maintained RSS drifted badly: 8 of 14 articles were missing entirely and
    4 of the 6 present had the wrong weekday in their RFC 2822 pubDate. Dates are
    formatted with email.utils so they are correct and locale-independent.
    """
    c = FEED_CHANNEL
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{escape(c['title'])}</title>",
        f"    <link>{c['link']}</link>",
        f"    <description>{escape(c['description'])}</description>",
        f"    <language>{c['language']}</language>",
        f'    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>',
    ]
    for a in articles:
        url = f"{BASE_URL}/{a['slug']}/"
        published = datetime.strptime(a["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        lines += [
            "    <item>",
            f"      <title>{escape(a['title'])}</title>",
            f"      <link>{url}</link>",
            f"      <pubDate>{format_datetime(published)}</pubDate>",
            f"      <description>{escape(a['description'])}</description>",
            f'      <guid isPermaLink="true">{url}</guid>',
            "    </item>",
        ]
    lines += ["  </channel>", "</rss>"]
    body = "\n".join(lines) + "\n"

    path = ROOT / "feed.xml"
    print(f"feed.xml      {len(articles)} items")
    if path.exists() and path.read_text(encoding="utf-8") == body:
        return []
    if write:
        path.write_text(body, encoding="utf-8")
    return ["feed.xml"]


# ── entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    check = "--check" in sys.argv[1:]
    write = not check

    stale = sync_partials(write)
    articles = load_manifest()
    stale += build_index(articles, write)
    stale += build_sitemap(articles, write)
    stale += build_feed(articles, write)

    if check:
        if stale:
            print("\nout of date — run `python3 _pipeline/build.py`:")
            for s in stale:
                print(f"  {s}")
            raise SystemExit(1)
        print("\nup to date")
    elif stale:
        print(f"\nupdated {len(stale)} file(s)")
    else:
        print("\nno changes")


if __name__ == "__main__":
    main()
