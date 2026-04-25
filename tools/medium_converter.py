#!/usr/bin/env python3
"""
Medium HTML → CannyForge article converter.

Usage:
  python3 tools/medium_converter.py <medium-html-file> [--category "Agent Systems"]

Outputs:
  - <slug>/index.html   ready to publish
  - manifest entry printed to stdout  (copy into manifest.json)
  - feed entry printed to stdout      (copy into feed.xml)

Run from the cannyforge-site root directory.
"""

import sys
import os
import re
import json
import argparse
from datetime import datetime
from bs4 import BeautifulSoup, Comment

CATEGORY_KEYWORDS = {
    "Agent Systems": ["agent", "agentic", "context engineering", "manus", "tool use", "memory", "alphago"],
    "Architecture":  ["attention", "transformer", "deepseek", "chain-of-thought", "react", "reasoning", "architecture", "moe"],
    "Analysis":      ["grok", "qwen", "apple", "openai", "benchmark", "comparison", "face-off", "minicpm"],
    "Tooling":       ["rag", "reranker", "cpu", "gpu", "tpu", "m1", "colab", "speed", "performance"],
    "Strategy":      ["panic", "advantage", "layers of intelligence", "policy", "optimization"],
}

def detect_category(title, body_text):
    text = (title + " " + body_text).lower()
    scores = {cat: sum(text.count(kw) for kw in kws) for cat, kws in CATEGORY_KEYWORDS.items()}
    return max(scores, key=scores.get)

def slugify(title):
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s-]", "", title)
    title = re.sub(r"\s+", "-", title.strip())
    title = re.sub(r"-+", "-", title)
    return title[:60].rstrip("-")

def clean_body(body_section):
    """Extract clean HTML from Medium body section."""
    if not body_section:
        return ""

    # Remove Medium embed link images (mixtapeImage)
    for el in body_section.find_all(class_="mixtapeImage"):
        el.decompose()

    # Remove empty iframes
    for el in body_section.find_all("figure", class_=lambda c: c and "graf--iframe" in c):
        el.decompose()

    # Remove section dividers
    for el in body_section.find_all("div", class_="section-divider"):
        el.decompose()

    # Remove HTML comments
    for comment in body_section.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Collect clean HTML elements
    output = []
    for section in body_section.find_all("section", class_="section"):
        inner = section.find("div", class_="section-inner")
        if not inner:
            continue
        for el in inner.children:
            if not hasattr(el, "name") or not el.name:
                continue
            output.append(clean_element(el))

    return "\n".join(filter(None, output))

def clean_element(el):
    """Convert a Medium element to clean semantic HTML."""
    # Title h3 → skip (already in masthead)
    if el.name in ("h3", "h4") and el.get("class") and "graf--title" in " ".join(el.get("class", [])):
        return ""

    # Headings
    if el.name in ("h1", "h2", "h3", "h4"):
        tag = "h2" if el.name in ("h1", "h2", "h3") else "h3"
        return f"<{tag}>{el.get_text()}</{tag}>"

    # Paragraphs
    if el.name == "p":
        inner = clean_inline(el)
        return f"<p>{inner}</p>" if inner.strip() else ""

    # Lists
    if el.name in ("ul", "ol"):
        items = "".join(f"<li>{clean_inline(li)}</li>" for li in el.find_all("li"))
        return f"<{el.name}>{items}</{el.name}>"

    # Blockquote
    if el.name == "blockquote":
        return f"<blockquote>{el.get_text()}</blockquote>"

    # Figures (images)
    if el.name == "figure":
        img = el.find("img")
        if img and img.get("src"):
            src = img["src"]
            caption = el.find("figcaption")
            cap_html = f"<figcaption>{caption.get_text()}</figcaption>" if caption else ""
            return f'<figure><img src="{src}" loading="lazy" style="max-width:100%;border-radius:4px;">{cap_html}</figure>'
        # mixtape embed (link card) → simple link
        link = el.find("a", class_="markup--anchor")
        if link:
            strong = link.find("strong")
            label = strong.get_text() if strong else link.get_text()
            href = link.get("href", "#")
            return f'<p><a href="{href}" target="_blank" rel="noopener">→ {label}</a></p>'
        return ""

    # Pre / code blocks
    if el.name == "pre":
        return f"<pre><code>{el.get_text()}</code></pre>"

    return ""

def clean_inline(el):
    """Clean inline content preserving links, bold, em, code."""
    parts = []
    for child in el.children:
        if isinstance(child, str):
            parts.append(child)
        elif child.name == "a":
            href = child.get("href", "#")
            parts.append(f'<a href="{href}" target="_blank" rel="noopener">{child.get_text()}</a>')
        elif child.name == "strong":
            parts.append(f"<strong>{child.get_text()}</strong>")
        elif child.name == "em":
            parts.append(f"<em>{child.get_text()}</em>")
        elif child.name == "code":
            parts.append(f"<code>{child.get_text()}</code>")
        elif child.name == "br":
            parts.append("<br>")
        elif child:
            parts.append(child.get_text())
    return "".join(parts)

def render_article(title, date_str, category, slug, body_html, description):
    pub_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — CannyForge</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="https://cannyforge.dev/{slug}/">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="CannyForge">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@cannyforge">
  <link rel="stylesheet" href="/assets/style.css">
  <link rel="alternate" type="application/rss+xml" title="CannyForge" href="/feed.xml">
  <style>
    .article-wrap {{ max-width: 720px; margin: 0 auto; padding: 0 20px 80px; }}
    .masthead {{ border-bottom: 2px solid var(--ink); padding: 32px 0 20px; margin-bottom: 40px; }}
    .masthead .kicker {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: .15em; color: var(--accent); margin-bottom: 8px; }}
    .masthead h1 {{ font-size: 36px; line-height: 1.2; letter-spacing: -.01em; margin-bottom: 12px; }}
    .masthead .byline {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 12px; color: var(--muted); }}
    .masthead .byline a {{ color: var(--accent); }}
    h2 {{ font-size: 22px; margin: 40px 0 14px; letter-spacing: -.01em; }}
    h3 {{ font-size: 18px; margin: 28px 0 10px; }}
    p {{ margin-bottom: 18px; font-size: 17px; line-height: 1.75; }}
    ul, ol {{ margin: 0 0 18px 24px; font-size: 17px; line-height: 1.75; }}
    li {{ margin-bottom: 6px; }}
    blockquote {{ border-left: 3px solid var(--accent); margin: 24px 0; padding: 4px 0 4px 20px; font-style: italic; color: var(--muted); }}
    pre {{ background: var(--surface); border-radius: 4px; padding: 16px; overflow-x: auto; margin: 24px 0; }}
    code {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 14px; background: var(--surface); padding: 2px 6px; border-radius: 3px; }}
    pre code {{ background: none; padding: 0; font-size: 13px; }}
    figure {{ margin: 28px 0; text-align: center; }}
    figure img {{ max-width: 100%; border-radius: 4px; }}
    figcaption {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 12px; color: var(--muted); margin-top: 8px; }}
    a, a:visited {{ color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }}
  </style>
</head>
<body>

<header class="site-header">
  <a href="/" class="site-name">Canny<span>Forge</span></a>
  <nav>
    <a href="/about.html">About</a>
    <a href="https://github.com/cannyforge" target="_blank" rel="noopener">GitHub</a>
    <a href="/feed.xml">RSS</a>
  </nav>
</header>

<div class="article-wrap">

<div class="masthead">
  <div class="kicker">{category} · {pub_date}</div>
  <h1>{title}</h1>
  <div class="byline">By <a href="/about.html">CannyForge</a></div>
</div>

{body_html}

<div class="author-box">
  <p>Written by <strong>CannyForge</strong> — AI systems engineering. We build <a href="https://github.com/cannyforge" target="_blank" rel="noopener">open-source observability tooling for AI agents</a> and write about what we learn.</p>
  <p style="margin-bottom:0">Follow on <a href="https://twitter.com/cannyforge" target="_blank" rel="noopener">Twitter/X</a> · <a href="/feed.xml">RSS</a> · <a href="/about.html">About</a></p>
</div>

<div class="email-capture">
  <p>Get new articles by email — no noise, just the writing.</p>
  <form action="https://buttondown.email/api/emails/embed-subscribe/BUTTONDOWN_USERNAME"
        method="post" target="popupwindow"
        onsubmit="window.open('https://buttondown.email/BUTTONDOWN_USERNAME','popupwindow')">
    <input type="email" name="email" placeholder="you@example.com" required>
    <button type="submit">Subscribe</button>
  </form>
</div>

<div class="comments">
  <script src="https://giscus.app/client.js"
    data-repo="cannyforge/cannyforge.github.io"
    data-repo-id="R_kgDOSMHeOA"
    data-category="General"
    data-category-id="DIC_kwDOSMHeOM4C7p9a"
    data-mapping="pathname"
    data-strict="0"
    data-reactions-enabled="1"
    data-emit-metadata="0"
    data-input-position="bottom"
    data-theme="preferred_color_scheme"
    data-lang="en"
    crossorigin="anonymous"
    async>
  </script>
</div>

</div>
</body>
</html>"""

def main():
    parser = argparse.ArgumentParser(description="Convert Medium HTML to CannyForge article")
    parser.add_argument("input", help="Medium HTML export file")
    parser.add_argument("--category", help="Override auto-detected category")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Title
    title_el = soup.find("h1", class_="p-name") or soup.find("title")
    title = title_el.get_text().strip()

    # Date from footer
    time_el = soup.find("time", class_="dt-published")
    if time_el and time_el.get("datetime"):
        date_str = time_el["datetime"][:10]
    else:
        # Fall back to filename date
        basename = os.path.basename(args.input)
        date_str = basename[:10]

    # Body
    body_section = soup.find("section", {"data-field": "body"})
    body_html = clean_body(body_section)

    # Description: first real paragraph text
    first_p = ""
    for p in (body_section or soup).find_all("p"):
        text = p.get_text().strip()
        if len(text) > 60:
            first_p = text[:200].rstrip() + "…"
            break

    # Category
    category = args.category or detect_category(title, body_html)

    # Slug
    slug = slugify(title)

    # Write article
    out_dir = slug
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render_article(title, date_str, category, slug, body_html, first_p))

    print(f"\n✓ Written: {out_path}")

    # Manifest entry
    manifest_entry = {
        "slug": slug,
        "title": title,
        "date": date_str,
        "category": category,
        "tags": [],
        "description": first_p,
    }
    print("\n── Manifest entry (add to manifest.json) ──")
    print(json.dumps(manifest_entry, indent=2))

    # RSS entry
    pub_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")
    print("\n── RSS entry (add to feed.xml inside <channel>) ──")
    print(f"""    <item>
      <title>{title}</title>
      <link>https://cannyforge.dev/{slug}/</link>
      <pubDate>{pub_date}</pubDate>
      <description>{first_p}</description>
      <guid isPermaLink="true">https://cannyforge.dev/{slug}/</guid>
    </item>""")

if __name__ == "__main__":
    main()
