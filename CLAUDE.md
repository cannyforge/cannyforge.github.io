# CannyForge Site — Publishing Workflow

This is the source for **cannyforge.dev** (served via GitHub Pages from `cannyforge/cannyforge.github.io`).  

---

## Directory structure

```
cannyforge-site/
├── index.html               ← Homepage (article list BAKED IN — see _pipeline/build.py)
├── about.html
├── 404.html
├── manifest.json            ← REQUIRED: source of truth, drives homepage + sitemap
├── feed.xml                 ← RSS feed (update alongside manifest.json)
├── robots.txt               ← Allows all crawlers incl. AI; points to sitemap
├── sitemap.xml              ← GENERATED — do not hand-edit
├── assets/
│   └── style.css            ← Shared styles for Tier 1 articles
├── _pipeline/
│   └── build.py             ← Regenerates index.html article list + sitemap.xml
├── _templates/
│   ├── tier1-article.html   ← Template for standard prose articles
│   └── tier2-survey.html    ← Template for pillar surveys (self-contained CSS)
└── <article-slug>/
    └── index.html           ← One directory per article
```

**`index.html` and `sitemap.xml` are generated.** The homepage article list used to
be fetched client-side, which meant crawlers saw only `Loading...`. It is now baked
into the HTML between `<!-- BEGIN:articles -->` / `<!-- END:articles -->` markers at
publish time. The remaining JS only wires up category filtering, reading
`data-category` off the DOM — no fetch. Never hand-edit inside the markers.

---

## Article tiers

### Tier 1 — Standard prose article

- Links to `/assets/style.css` for shared styles
- Uses system fonts (Helvetica Neue / SF Mono); serif not required
- Simple layout: masthead → body → author box → email capture → Giscus
- Template: `_templates/tier1-article.html`

### Tier 2 — Pillar survey / long-form analysis

- **Self-contained**: all CSS embedded in `<style>` block, no `/assets/style.css` link
- Design system: **Fraunces** (serif display) + **JetBrains Mono** (mono) + **Inter Tight** (sans)
- CSS variables: `--ink`, `--paper`, `--paper-deep`, `--rust`, `--rust-deep`, `--olive`, `--gold`
- Sections numbered `§ 01`, `§ 02`, … with `.section-label` + `.reveal` classes
- Ends with a **Dig Deeper** block listing 7 cluster posts (Coming Soon or live links)
- Template: `_templates/tier2-survey.html`

---

## Adding a new article — step by step

### 1. Create the article directory and file

```bash
mkdir cannyforge-site/<slug>
# Copy the appropriate template:
cp cannyforge-site/_templates/tier1-article.html cannyforge-site/<slug>/index.html
# or for surveys:
cp cannyforge-site/_templates/tier2-survey.html cannyforge-site/<slug>/index.html
```

Replace all `PLACEHOLDER` tokens (ARTICLE_TITLE, ARTICLE_SLUG, etc.) with real values.

### 2. Update `manifest.json`

Add a new entry at the **top** of the array (newest first):

```json
{
  "slug": "your-article-slug",
  "title": "Full Article Title",
  "date": "YYYY-MM-DD",
  "category": "Agent Systems",
  "tags": ["tag1", "tag2", "tag3"],
  "description": "One or two sentence description shown on the homepage card."
}
```

**Valid categories**: `Agent Systems`, `Architecture`, `Analysis`

### 3. Update `feed.xml`

Add a new `<item>` block immediately after the opening `<channel>` tags, before any existing items:

```xml
<item>
  <title>Full Article Title</title>
  <link>https://cannyforge.dev/your-article-slug/</link>
  <pubDate>Day, DD Mon YYYY 00:00:00 +0000</pubDate>
  <description>Same description as manifest.json.</description>
  <guid isPermaLink="true">https://cannyforge.dev/your-article-slug/</guid>
</item>
```

Date format: `Wed, 21 May 2026 00:00:00 +0000` (RFC 2822).

### 4. Run the build

```bash
python3 _pipeline/build.py
```

Regenerates the homepage article list and `sitemap.xml` from `manifest.json`.
Safe to run repeatedly — output is idempotent. **Skipping this means the new
article never appears on the homepage or in the sitemap.**

### 5. Check the article's own page

Every article needs the goatcounter snippet before `</body>` and a working
Buttondown form (`embed-subscribe/cannyforge` — never a placeholder). Both are
already in the templates; verify they survived if you hand-edited:

```bash
grep -L goatcounter */index.html                 # should list nothing
grep -rl BUTTONDOWN_USERNAME . --include=*.html  # should list nothing
```

---

## Slug naming convention

- Lowercase, hyphen-separated
- Remove stop words; keep meaningful nouns/verbs
- Max ~60 characters (GitHub Pages path limit is not an issue, but keep it readable)
- Examples:
  - `the-state-of-agent-frameworks-2026`
  - `context-engineering-the-real-secret-to-magical-ai-agents`
  - `deepseek-v4`

---

## Pillar + cluster content model

A **Tier 2 survey** (pillar) spawns **7 cluster posts** that each deep-dive one angle.  
The pillar's "Dig Deeper" section links to all 7. Cluster posts are Tier 1 articles.

### Cluster post pattern

Each cluster post:
1. Lives at its own slug (e.g., `openai-agents-sdk-deep-dive`)
2. References the parent survey with a link: `← Part of the State of Agent Frameworks 2026 survey`
3. Is registered in `manifest.json` and `feed.xml` independently
4. Tags should include the parent survey's primary tag (e.g., `survey`, `frameworks`)

When a cluster post goes live, update the parent survey's "Dig Deeper" section:
- Change `<span class="cc-badge soon">Coming Soon</span>` to:
  `<a class="cc-badge live" href="/cluster-slug/">Read →</a>`

---

## CSS quick reference (Tier 2)

| Pattern | Element | Key attributes |
|---------|---------|---------------|
| Section number | `.section-label.reveal` | `§ 01` text, `--rust` color |
| Section heading | `h2.reveal` | Fraunces 600, clamp(24px–36px) |
| Scroll reveal | `.reveal` → `.reveal.in` | opacity 0→1, translateY 20px→0 |
| Tab bar | `.tabs > .tab[data-target]` | active class = `--rust` border |
| Tab content | `.tab-panel#ID` | `display:none`; `.active` = `display:block` |
| Bar chart | `.bar-fill[data-pct]` | pct capped at 200 → `pct/2 %` width |
| Token chart | `.token-seg[data-w]` | direct `%` width; classes `seg-hist/task/out` |
| Framework matrix | `.fw-matrix > .fw-row > .fw-name-cell` | rust left border |
| Code compare | `.code-compare > .code-compare-side` | 2-col grid, dark bg |
| Tag badge | `.tag` | mono 11px, paper-deep bg |
| Cluster card | `.cluster-card` | ink bg, hover lightens |
| Coming Soon | `.cc-badge.soon` | gold, `--gold` color |
| Live link | `.cc-badge.live` | rust, links to post |

---

## Site header (both tiers)

Always use this exact markup — it matches the site-wide sticky header:

```html
<header class="site-header">
  <a href="/" class="site-name">Canny<span>Forge</span></a>
  <nav>
    <a href="/about.html">About</a>
    <a href="https://github.com/cannyforge" target="_blank" rel="noopener">GitHub</a>
    <a href="/feed.xml">RSS</a>
  </nav>
</header>
```

For Tier 2, the `.site-header` styles are embedded in the `<style>` block.  
For Tier 1, the styles come from `/assets/style.css`.

---

## Giscus comments

Already configured. Copy this block verbatim into every article footer:

```html
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
```

`data-mapping="pathname"` means each article gets its own comment thread automatically.

---

## Deployment

The site deploys automatically via GitHub Pages on push to `main`.  
No build step *at serve time* — all HTML/CSS/JS is pre-rendered, which is why
`_pipeline/build.py` must run before you commit.

```bash
python3 _pipeline/build.py
git add <slug>/index.html manifest.json feed.xml index.html sitemap.xml
git commit -m "add: <article title>"
git push
```

Live in ~30 seconds at `https://cannyforge.dev/<slug>/`.
