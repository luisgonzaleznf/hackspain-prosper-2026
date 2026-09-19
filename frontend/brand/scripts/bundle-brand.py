#!/usr/bin/env python3
"""Bundle brand/index.html into one self-contained HTML file (dist/rosario-brand.html).

Inlines tokens.css + brand.css (fonts as base64 data URIs) and every
<i data-mark="..."> as the normalized SVG, so the page needs no server and can
be published as an Artifact. Strips the <!doctype>/<html>/<head>/<body>
wrapper because the Artifact host supplies its own; the local file keeps them.
"""
import base64
import re
from pathlib import Path

BRAND = Path(__file__).resolve().parent.parent
FRONTEND = BRAND.parent
DIST = BRAND / "dist"
DIST.mkdir(exist_ok=True)

html = (BRAND / "index.html").read_text(encoding="utf-8")
tokens = (FRONTEND / "tokens" / "tokens.css").read_text(encoding="utf-8")
brand_css = (BRAND / "brand.css").read_text(encoding="utf-8")


def inline_font(match: re.Match) -> str:
    rel = match.group(1)
    data = (FRONTEND / "tokens" / rel).resolve().read_bytes()
    return f'url("data:font/woff2;base64,{base64.b64encode(data).decode()}")'


tokens = re.sub(r'url\("(\.\./fonts/[^"]+)"\)', inline_font, tokens)
brand_css = brand_css.replace('@import url("../tokens/tokens.css");', tokens)

marks = {}
def inline_mark(match: re.Match) -> str:
    name = match.group(1)
    if name not in marks:
        marks[name] = (BRAND / "logos" / "marks" / f"{name}.svg").read_text(encoding="utf-8").strip()
    return f'<i data-mark="{name}">{marks[name]}</i>'


html = re.sub(r'<i data-mark="([^"]+)"></i>', inline_mark, html)


def inline_file(match: re.Match) -> str:
    name = match.group(1)
    svg = (BRAND / "logos" / "final" / f"{name}.svg").read_text(encoding="utf-8").strip()
    return f'<i data-file="{name}">{svg}</i>'


html = re.sub(r'<i data-file="([^"]+)"></i>', inline_file, html)
html = html.replace('<link rel="stylesheet" href="brand.css">', f"<style>\n{brand_css}\n</style>")
html = html.replace('<script src="brand.js"></script>\n', "")

# Artifact variant: body content only, title + style kept at the top.
title = re.search(r"<title>.*?</title>", html).group(0)
style = re.search(r"<style>.*?</style>", html, flags=re.S).group(0)
body = re.search(r"<body>(.*)</body>", html, flags=re.S).group(1)
(DIST / "rosario-brand.html").write_text(f"{title}\n{style}\n{body}", encoding="utf-8")
(DIST / "rosario-brand-standalone.html").write_text(html, encoding="utf-8")
print("bundled", len(marks), "marks;", (DIST / "rosario-brand.html").stat().st_size // 1024, "KB")
