#!/usr/bin/env python3
"""
Generate OG image for The Last Free Tier.
Output: assets/og-the-last-free-tier.png  (1200 x 630)
Usage:  python3 assets/gen-og-fiction.py
"""

from PIL import Image, ImageDraw, ImageFont
import math, os

W, H = 1200, 630
img = Image.new("RGB", (W, H), "#06091a")
d   = ImageDraw.Draw(img)

# ── Sky gradient ──────────────────────────────────────────────────────────────
for y in range(H):
    t = y / H
    r = int(6  + t * 12)
    g = int(9  + t * 18)
    b = int(26 + t * 30)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# ── Stars ─────────────────────────────────────────────────────────────────────
stars = [
    (80,40,1),(200,25,1),(340,55,1),(460,30,1),(580,18,1),(720,42,1),
    (850,28,1),(980,50,1),(1100,33,1),(1160,65,1),(150,80,1),(300,95,1),
    (430,70,1),(560,88,1),(690,60,1),(820,74,1),(950,83,1),(1050,48,1),
    (50,110,1),(250,120,1),(390,98,1),(510,105,1),(640,115,1),(770,92,1),
    (900,108,1),(1030,75,1),(1120,100,1),(170,140,1),(320,130,1),(480,145,1),
    (700,135,1),(1000,125,1),(75,60,2),(450,45,2),(880,38,2),(1140,90,2),
]
for x, y, r in stars:
    alpha = 180 if r == 1 else 230
    d.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255, alpha))

# ── Building silhouettes ───────────────────────────────────────────────────────
horizon = 380
bld_color = (13, 22, 42)
bld_lit   = (25, 45, 80)

buildings = [
    (0,   horizon-55,  38, 55),
    (42,  horizon-85,  55, 85),
    (100, horizon-130, 42, 130),
    (146, horizon-60,  38, 60),
    (188, horizon-105, 68, 105),
    (260, horizon-155, 46, 155),  # tallest — Salesforce tower
    (310, horizon-75,  42, 75),
    (356, horizon-110, 52, 110),
    (412, horizon-55,  40, 55),
    (456, horizon-80,  32, 80),
    (492, horizon-50,  38, 50),
    (534, horizon-90,  36, 90),
    (574, horizon-65,  44, 65),
    (622, horizon-48,  30, 48),
]
for bx, by, bw, bh in buildings:
    d.rectangle([bx, by, bx+bw, horizon], fill=bld_color)
    # Lit windows
    for wy in range(by + 10, horizon - 8, 18):
        for wx in range(bx + 5, bx + bw - 5, 10):
            if (wx + wy) % 3 != 0:
                d.rectangle([wx, wy, wx+3, wy+5], fill=(40, 70, 110))

# ── Water ─────────────────────────────────────────────────────────────────────
for y in range(horizon, H):
    t = (y - horizon) / (H - horizon)
    r = int(6  + t * 4)
    g = int(12 + t * 6)
    b = int(26 + t * 10)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# ── Bay Bridge ────────────────────────────────────────────────────────────────
deck_y    = horizon - 4
cable_col = (45, 70, 110)
tower_col = (35, 60, 100)
amber     = (245, 170, 50)

# Road deck
d.rectangle([0, deck_y, W, deck_y + 8], fill=(20, 35, 60))

# Towers
tw = 10  # tower width
# Left tower: x=650
ltx = 650
d.rectangle([ltx, deck_y - 160, ltx+tw, deck_y], fill=tower_col)
# Tower top crossbar
d.rectangle([ltx-8, deck_y-162, ltx+tw+8, deck_y-150], fill=tower_col)
# Tower light
d.ellipse([ltx, deck_y-175, ltx+tw, deck_y-162], fill=amber)

# Right tower: x=870
rtx = 870
d.rectangle([rtx, deck_y - 155, rtx+tw, deck_y], fill=tower_col)
d.rectangle([rtx-8, deck_y-157, rtx+tw+8, deck_y-145], fill=tower_col)
d.ellipse([rtx, deck_y-170, rtx+tw, deck_y-157], fill=amber)

# Main cables (simplified bezier via polyline)
def cable_pts(x1, y1, x2, y2, x3, y3, steps=40):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1-t)**2 * x1 + 2*(1-t)*t * x2 + t**2 * x3
        y = (1-t)**2 * y1 + 2*(1-t)*t * y2 + t**2 * y3
        pts.append((int(x), int(y)))
    return pts

# West cable (left tower → west end)
pts = cable_pts(ltx+5, deck_y-160, 300, deck_y-60, 0, deck_y)
d.line(pts, fill=cable_col, width=2)

# Mid cable (left tower → right tower)
pts = cable_pts(ltx+5, deck_y-160, 760, deck_y-80, rtx+5, deck_y-155)
d.line(pts, fill=cable_col, width=2)

# East cable (right tower → east end)
pts = cable_pts(rtx+5, deck_y-155, 1050, deck_y-70, W, deck_y)
d.line(pts, fill=cable_col, width=2)

# Bridge lights along deck
for bx in range(30, W, 40):
    d.ellipse([bx-2, deck_y-3, bx+2, deck_y+3], fill=(200, 140, 40))

# Water reflections
for rx, ry_start, ht, rw, brightness in [
    (655, horizon+4, 40, 3, 60),
    (875, horizon+4, 38, 3, 60),
    (200, horizon+4, 25, 2, 30),
    (400, horizon+4, 20, 2, 25),
]:
    for i in range(ht):
        alpha = int(brightness * (1 - i / ht))
        d.rectangle([rx, ry_start+i, rx+rw, ry_start+i+1], fill=(alpha, alpha//2, 0))

# ── Terminal window (top-right) ───────────────────────────────────────────────
tx, ty, tw2, th = 730, 80, 420, 160
# Window bg
d.rectangle([tx, ty, tx+tw2, ty+th], fill=(8, 16, 30), outline=(50, 90, 140), width=1)
# Header bar
d.rectangle([tx, ty, tx+tw2, ty+28], fill=(15, 28, 52))
# Traffic light dots
for dx, dc in [(14, (200,60,60)), (30, (200,160,60)), (46, (60,180,60))]:
    d.ellipse([tx+dx-4, ty+10, tx+dx+4, ty+18], fill=dc)
# Title
try:
    font_mono = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 11)
    font_title = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 10)
except:
    font_mono = font_title = ImageFont.load_default()

d.text((tx+65, ty+9), "atlas — session", font=font_title, fill=(120, 150, 200))
# Code lines
d.text((tx+16, ty+44), "$ atlas implement stripe integration", font=font_mono, fill=(50, 220, 100))
d.text((tx+16, ty+68), "> Planning... scaffolding... committing", font=font_mono, fill=(100, 160, 230))
d.text((tx+16, ty+92), "✓  847 lines committed  ·  6m 43s", font=font_mono, fill=(90, 110, 150))
d.text((tx+16, ty+116), "$ _", font=font_mono, fill=(50, 220, 100))

# Terminal glow
for r in range(20, 0, -1):
    alpha = int(8 * (1 - r/20))
    d.rectangle([tx-r, ty-r, tx+tw2+r, ty+th+r],
                outline=(30, 80, 160, alpha), width=1)

# ── Fog gradient at horizon ───────────────────────────────────────────────────
for y in range(horizon - 60, horizon + 20):
    t = (y - (horizon - 60)) / 80
    alpha = int(18 * math.sin(t * math.pi))
    if alpha > 0:
        d.line([(0, y), (W, y)], fill=(160, 180, 210, alpha))

# ── Title text overlay ────────────────────────────────────────────────────────
try:
    font_h1   = ImageFont.truetype("/System/Library/Fonts/Georgia.ttf", 72)
    font_sub  = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 18)
    font_site = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 14)
except:
    try:
        font_h1  = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", 72)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_site = font_sub
    except:
        font_h1 = font_sub = font_site = ImageFont.load_default()

# Dark scrim at bottom for text legibility
for y in range(horizon - 100, H):
    t = (y - (horizon - 100)) / (H - horizon + 100)
    alpha = int(160 * min(t * 1.4, 1))
    d.line([(0, y), (W, y)], fill=(4, 8, 18, alpha))

# FICTION · CANNYFORGE label
d.text((68, H - 180), "FICTION  ·  CANNYFORGE", font=font_site,
       fill=(120, 160, 220))

# Title
d.text((64, H - 155), "The Last Free Tier", font=font_h1, fill=(240, 238, 232))

# Tagline
d.text((68, H - 58),
       "A story about platform dependency, developer lock-in, and what it costs to stay competitive.",
       font=font_sub, fill=(140, 160, 190))

# ── Save ─────────────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(__file__), "og-the-last-free-tier.png")
img.save(out, "PNG", optimize=True)
print(f"Saved: {out}  ({W}×{H})")
