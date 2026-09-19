#!/usr/bin/env python3
"""Normalize a QuiverAI logo SVG into a brand mark that colors from CSS.

- drops the full-canvas background rect and the generator comment
- drops gradient defs; every colored fill/stroke becomes currentColor
- black fills (the cut-outs) become var(--logo-bg, #000) so the mark works on
  red or white grounds when the host sets --logo-bg
- removes width/height so the viewBox scales to its container

Usage: normalize-logo.py <in.svg> <out.svg>
"""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
svg = open(src, encoding="utf-8").read()

svg = re.sub(r"<!--.*?-->\s*", "", svg, flags=re.S)
svg = re.sub(r"<defs>.*?</defs>\s*", "", svg, flags=re.S)
svg = re.sub(r'<rect id="black-background"[^>]*/>\s*', "", svg)
svg = re.sub(r'<rect[^>]*fill="#000(?:000|100)?"[^>]*/>\s*', "", svg, count=1)
# Some outputs draw the canvas as a full-size path (M0 0 H<w> V<h> H0 Z), sometimes with
# no fill attribute at all (black by SVG default). Drop it too, whatever its fill.
svg = re.sub(r'<path[^>]*\bd="[Mm]0[ ,]0\s*[Hh]\s*[\d.]+\s*[Vv]\s*[\d.]+\s*[Hh]\s*0\s*[Zz]"[^>]*/>\s*', "", svg)
svg = re.sub(r'<path[^>]*\bd="[Mm]0[ ,]0\s*[Hh]\s*[\d.]+\s*[Vv]\s*[\d.]+\s*[Hh]\s*0\s*[Zz]"[^>]*>\s*</path>\s*', "", svg)

BLACK = re.compile(r'(fill|stroke)="#(?:000|000000|000100|010101)"')
svg = BLACK.sub(r'\1="var(--logo-bg, #000)"', svg)
COLORED = re.compile(r'(fill|stroke)="(?:#[0-9a-fA-F]{3,8}|url\(#[^)]*\)|rgb[^"]*)"')
svg = COLORED.sub(r'\1="currentColor"', svg)

svg = re.sub(r'<svg([^>]*?)\s+width="[^"]*"\s+height="[^"]*"', r"<svg\1", svg, count=1)
svg = svg.replace("<svg ", '<svg fill="currentColor" ', 1)

open(dst, "w", encoding="utf-8").write(svg)
print(dst, len(svg), "bytes")
