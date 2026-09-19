#!/usr/bin/env python3
"""Build final ROSARIO logo assets from a chosen mark and the brand font.

Outputs into brand/logos/final/:
  mark.svg               the mark, currentColor, square viewBox
  lockup-horizontal.svg  mark + ROSARIO wordmark (font outlines, no text nodes)
  lockup-stacked.svg     mark above the wordmark
  wordmark.svg           wordmark alone
  favicon-{16,32,180,512}.png  red mark on Inkline Crimson, via headless Chromium

Usage: build-lockups.py <mark.svg> [word]
The wordmark is lowercase Plain Light (Galileo lockup: glyph + lowercase word, weight 300),
converted to paths with fontTools so the SVG needs no font.
"""
import re
import subprocess
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent
FONT = BRAND.parent / "fonts" / "plain" / "plain-light.woff2"
OUT = BRAND / "logos" / "final"
CHROME = Path.home() / ".cache/ms-playwright/chromium_headless_shell-1223/chrome-linux/headless_shell"

mark_path = Path(sys.argv[1])
word = sys.argv[2] if len(sys.argv) > 2 else "rosario"
OUT.mkdir(parents=True, exist_ok=True)

# --- mark: reuse the normalized SVG, read its viewBox ---------------------
mark_svg = mark_path.read_text(encoding="utf-8")
vb = re.search(r'viewBox="([\d.\s-]+)"', mark_svg).group(1).split()
mx, my, mw, mh = map(float, vb)
mark_inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", mark_svg.strip(), flags=re.S)
(OUT / "mark.svg").write_text(mark_svg, encoding="utf-8")

# --- wordmark: glyph outlines from the variable font at wght 700 -----------
font = TTFont(FONT)  # Plain Light, static; the Galileo lockup sets the word in weight 300
glyph_set = font.getGlyphSet()
cmap = font.getBestCmap()
upem = font["head"].unitsPerEm
CAP = 700  # cap height in SVG units; lowercase word so the x-height sits at about 0.7 CAP
scale = CAP / font["OS/2"].sCapHeight
tracking = -0.01 * CAP  # slight negative tracking, lowercase Plain Light

paths, x = [], 0.0
for ch in word:
    gname = cmap[ord(ch)]
    pen = SVGPathPen(glyph_set)
    # flip y (font y up, SVG y down) and scale to CAP
    tpen = TransformPen(pen, (scale, 0, 0, -scale, x, CAP))
    glyph_set[gname].draw(tpen)
    paths.append(f'<path d="{pen.getCommands()}"/>')
    x += glyph_set[gname].width * scale + tracking
word_w = x - tracking
word_h = CAP
# Two-tone lockup: the mark takes currentColor, the word takes --logo-word (white by default).
word_group = f'<g id="wordmark" fill="var(--logo-word, #FEFEFE)">{"".join(paths)}</g>'

(OUT / "wordmark.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 {-0.02 * CAP:.0f} {word_w:.0f} {word_h * 1.06:.0f}">{word_group}</svg>\n',
    encoding="utf-8",
)

# --- horizontal lockup: mark at cap height, gap = 0.45 cap ----------------
gap = 0.45 * CAP
mark_scale = (CAP * 1.18) / mh  # mark slightly taller than caps, optically balanced
mark_w = mw * mark_scale
mark_y = (CAP - mh * mark_scale) / 2
total_w = mark_w + gap + word_w
pad = 0.15 * CAP
horizontal = (
    f'<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" '
    f'viewBox="{-pad:.0f} {-pad:.0f} {total_w + 2 * pad:.0f} {CAP + 2 * pad:.0f}">'
    f'<g id="mark" transform="translate(0 {mark_y:.1f}) scale({mark_scale:.5f}) translate({-mx} {-my})">{mark_inner}</g>'
    f'<g transform="translate({mark_w + gap:.1f} 0)">{word_group}</g></svg>\n'
)
(OUT / "lockup-horizontal.svg").write_text(horizontal, encoding="utf-8")

# --- stacked lockup: mark centered above the word --------------------------
sm = (CAP * 2.2) / mh
smw = mw * sm
stack_w = max(smw, word_w)
stack_gap = 0.5 * CAP
stacked = (
    f'<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" '
    f'viewBox="{-pad:.0f} {-pad:.0f} {stack_w + 2 * pad:.0f} {mh * sm + stack_gap + CAP + 2 * pad:.0f}">'
    f'<g id="mark" transform="translate({(stack_w - smw) / 2:.1f} 0) scale({sm:.5f}) translate({-mx} {-my})">{mark_inner}</g>'
    f'<g transform="translate({(stack_w - word_w) / 2:.1f} {mh * sm + stack_gap:.1f})">{word_group}</g></svg>\n'
)
(OUT / "lockup-stacked.svg").write_text(stacked, encoding="utf-8")

# --- favicons: red mark on black, rendered by headless Chromium -----------
for size in (16, 32, 180, 512):
    html = OUT / f"_fav{size}.html"
    html.write_text(
        f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#2d1012}}'
        f'body{{width:{size}px;height:{size}px;display:grid;place-items:center;color:#fe0600}}'
        f'svg{{width:{size * 0.92:.0f}px;height:{size * 0.92:.0f}px}}</style>{mark_svg}',
        encoding="utf-8",
    )
    subprocess.run(
        [str(CHROME), "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         f"--window-size={size},{size}", f"--screenshot={OUT / f'favicon-{size}.png'}", html.as_uri()],
        check=True, capture_output=True,
    )
    html.unlink()

print("built:", sorted(p.name for p in OUT.iterdir()))
