#!/usr/bin/env python3
"""Regenerate derived files from manifest.json.

Run from the repo root after editing manifest.json:

    python3 _pipeline/build.py

Generates:
  - index.html   article list + filter chips, baked between BEGIN/END markers so
                 crawlers see the articles instead of "Loading..."
  - sitemap.xml  every article plus the static pages

Both outputs are committed. The site still has no build step at serve time —
this just moves the rendering from the visitor's browser to publish time.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://cannyforge.dev"
STATIC_PAGES = ["/", "/about.html"]


def load_manifest() -> list[dict]:
    articles = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


def replace_block(text: str, name: str, body: str) -> str:
    """Swap the content between <!-- BEGIN:name --> and <!-- END:name -->.

    Emits fixed surrounding whitespace so the markers always land on their own
    lines — otherwise regenerated blocks produce noisy diffs.
    """
    pattern = re.compile(
        rf"<!-- BEGIN:{name} -->.*?<!-- END:{name} -->",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"marker BEGIN:{name}/END:{name} not found — cannot build")
    replacement = f"<!-- BEGIN:{name} -->\n{body}\n  <!-- END:{name} -->"
    return pattern.sub(lambda _: replacement, text)


def render_chips(articles: list[dict]) -> str:
    seen: list[str] = []
    for a in articles:
        if a["category"] not in seen:
            seen.append(a["category"])
    return "\n".join(
        f'    <button class="chip" data-category="{escape(c, quote=True)}">{escape(c)}</button>'
        for c in seen
    )


def render_articles(articles: list[dict]) -> str:
    out = []
    for a in articles:
        out.append(
            f'    <a href="/{escape(a["slug"], quote=True)}/" class="article-item" '
            f'data-category="{escape(a["category"], quote=True)}">\n'
            f'      <div class="meta">\n'
            f'        <time datetime="{escape(a["date"], quote=True)}">{escape(a["date"])}</time>\n'
            f'        <span class="category-badge">{escape(a["category"])}</span>\n'
            f'      </div>\n'
            f'      <h2>{escape(a["title"])}</h2>\n'
            f'      <p>{escape(a["description"])}</p>\n'
            f'    </a>'
        )
    return "\n".join(out)


def build_index(articles: list[dict]) -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    text = replace_block(text, "filters", render_chips(articles))
    text = replace_block(text, "articles", render_articles(articles))
    path.write_text(text, encoding="utf-8")
    print(f"index.html    {len(articles)} articles baked in")


def build_sitemap(articles: list[dict]) -> None:
    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc in STATIC_PAGES:
        lines += [f"  <url>\n    <loc>{BASE_URL}{loc}</loc>\n"
                  f"    <lastmod>{today}</lastmod>\n  </url>"]
    for a in articles:
        lines += [f"  <url>\n    <loc>{BASE_URL}/{a['slug']}/</loc>\n"
                  f"    <lastmod>{a['date']}</lastmod>\n  </url>"]
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml   {len(articles) + len(STATIC_PAGES)} urls")


def main() -> None:
    articles = load_manifest()
    build_index(articles)
    build_sitemap(articles)


if __name__ == "__main__":
    main()
