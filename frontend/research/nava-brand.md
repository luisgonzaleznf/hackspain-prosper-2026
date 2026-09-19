# Nava brand archaeology: the red/burgundy identity vs the gold site

Research date: 2026-09-18. Source page: https://www.rebrand.gallery/rebrand/nava

## 0. The one thing to know first

The rebrand.gallery entry and the "current gold site" are two different companies that share a name.

- The BURGUNDY/RED identity (the one the user wants) belongs to **Nava Labs** (product "Nava AI"), a New York crypto/AI startup building a verification and escrow layer for autonomous financial agents. Real website: **https://navalabs.ai**. Identity by **Wednesday Studio** (Brooklyn), published June 2026. Colors are literally named "Nava Red" and "Nava Fire" in the rebrand.gallery data; the deep red #BC0400 is filed under the gallery's "Burgundy" color family, which is where the "burgundy" label comes from.
- The GOLD site at **https://nava.com** belongs to **Nava (formerly Kluisz.ai)**, a Bengaluru AI-native cloud company (founders Abhinav Sinha, Abhijeet Singh, Vamshidhar Reddy). rebrand.gallery lists nava.com as the "Company website" and copied its tags ("ai cloud", "gpu compute", "data centers"). That link is wrong: the rebrand video shows "Guardrails for Autonomous Agents", "Nava Verifies" and the investors Polychain, Hack VC, FalconX, which is navalabs.ai content.

So the red/burgundy design is not an older version of the gold site. It is the live, current identity of a different Nava. Both are documented below; the burgundy one in full.

## 1. Who Nava is, and the two design eras

### Nava Labs (navalabs.ai), the burgundy/red brand

- Founders: Vyas Krishnan (CEO, first employee and product lead at EigenLayer) and Brianna Montgomery (ex-EigenLayer). Research talent from Carnegie Mellon.
- Product: "Nava Arbiter" / "Guardian" verifies every agent-proposed transaction (intent alignment, parameter validity, adversarial manipulation) before an MPC escrow executes it. Runs as an L3 on Arbitrum, parallel deployment on Tempo planned, NavaUSD stablecoin planned.
- 14 Apr 2026: out of stealth with an $8.3M seed co-led by Polychain Capital and Archetype, plus Hack VC, FalconX, Seed Club Ventures, Sreeram Kannan (Fortune, Globe and Mail, LinkedIn).
- 8 Jun 2026: first Wayback capture of navalabs.ai already shows the red identity, Muoto Trial webfonts, headline "Guardrails for Autonomous Agents".
- 11 Jun 2026: rebrand video uploaded to Vimeo (1200404689, "Nava Rebrand", account Sahkyo, 33 s) and the rebrand.gallery record created (agency: Wednesday, industry: Tech, year 2026).
- 15 Jun 2026: Nava AI LinkedIn post, "we built an identity inspired by the idea of a guardian".
- Sep 2026 (live): same identity, headline now "Guardrails for Agentic Finance", nav Products / About / Docs / Blog / Request Demo.
- Pre-rebrand look: unverified. The company was in stealth before April 2026 and there is only one Wayback capture of navalabs.ai. Sibling domain navalabs.xyz has captures Sep 2024 to Mar 2025 but currently serves an empty page and was not confirmed to be the same company.

### Nava / Kluisz.ai (nava.com), the gold brand

- nava.com was a parked "domain for sale" page in every Wayback capture from Apr 2024 through 15 Mar 2026.
- kluisz.ai (Dec 2025 capture) was still "Kluisz.ai - Next Gen Cloud". Crunchbase lists Nava "also known as Kluisz.ai", Bengaluru, Series A, investors Unicorn India Ventures, Greenoaks, RTP Global, Blume.
- Sep 2026 (live): nava.com is a Next.js + Tailwind + shadcn site, "NAVA - AI-Native Cloud Platform", dark olive/gold hero, cream sections, dark green accents. Launched somewhere between Mar and Sep 2026 (exact date unverified).

## 2. BURGUNDY palette (Nava Labs, Wednesday Studio identity)

All values below come from the live navalabs.ai CSS (`:root` variables and utility classes), the rebrand.gallery record, and pixel sampling of the rebrand video. Role labels are inferred from usage.

| Hex | Name / source | Role | Evidence |
|---|---|---|---|
| #000000 | `--color-bg`, "Nava Black" | Page background, nav (rgba(0,0,0,0.86) with 15px backdrop blur) | body bg rgb(0,0,0); rebrand.gallery |
| #0D0D0D | `--color-card` | Card fill (often at 80% over the red glow: #0d0d0dcc) | CSS var |
| #191919 | `--color-dark` | Elevated dark surface, table rows | CSS var |
| #1E1E1E | (utility, 94% alpha #1e1e1ef0) | Panel / dropdown fill | CSS |
| #FE0600 | `--color-red`, "Nava Red" | Primary brand red: logo on black, CTA gradient top, section eyebrow labels, glow shadows, `--color-bg-primary` = #fe0600b3 | CSS var; rebrand.gallery; 109 uses |
| #BC0400 | "Nava Fire" | Deep red: bottom of hero gradient, pressed/darker red surfaces. Gallery files it under color family "Burgundy" (#9B1B30) | rebrand.gallery; CSS 3 uses |
| #EC0000 | (utility) | Red border / solid red badge fill | CSS 12 uses |
| #ED0600 / #E60300 / #DA0500 / #AA0400 | gradient stops | Primary button gradient `#E60300 -> #AA0400`; hover `#FF0300 -> #DA0500` | CSS |
| #FF5141 | inset highlight | Inner top highlight on red buttons: `inset 0 2px 2px #ff5141, 0 0 8px #fe0600` | CSS |
| #DB8989 (46%) | inset highlight | Inner top highlight on ghost/outlined pills: `inset 0 1px 1px #db898975` | computed styles |
| #900000 / #780000 / #180000 | video-sampled | Dark red falloff of the dotted "scale" texture and page-bottom bleed | frame pixel counts |
| #FEFEFE | `--color-white`, "Nava White" | Headings, nav text, logo on red | body color rgb(254,254,254) |
| #FFFFFF at 65% | `--color-grey` (#ffffffa6) | Body copy, subheads | p color = white / 0.65 |
| #FFFFFF at 15% / 19% / 5% | `color-mix(white N%)` | Hairline borders on cards, inputs, table cells | CSS borders |
| #FFFFFF at 19% (#ffffff30) | border | Input outline | CSS |
| #FE0600 at 40% (#fe060066) | border | Red keyline on active step | CSS |
| #D3D3D3 | (utility) | Muted grey text in mono labels | CSS 2 uses |
| #000000 at 60% (#0009) | `--color-grey-on-light` | Grey text when on a light surface (rare) | CSS var |

Notes:
- rebrand.gallery publishes exactly four swatches: #FE0600 Nava Red, #BC0400 Nava Fire, #000000 Nava Black, #FEFEFE Nava White. Everything else above is implementation detail from the site.
- The "Burgundy" #9B1B30 is the gallery's taxonomy swatch, not a Nava color. The brand never uses a true burgundy; it uses pure red on black and lets the red fall off into near-black (#BC0400 -> #900000 -> #180000) through gradients and a 3D dotted texture.
- Hero gradient (video frame 28 and live site): red radial "scale" pattern behind the header, page fades top black -> #FE0600 mid -> #BC0400 bottom. CSS: `linear-gradient(#fe060000 18.98%, #fe0600 100.7%)` over `#0003`, plus large glows `0 65px 135px 18px #fe0600`.

## 3. GOLD palette (nava.com, Kluisz.ai) for contrast

From nava.com CSS variables (shadcn HSL tokens) and utilities, plus computed styles.

| Hex | Source | Role |
|---|---|---|
| #312404 | `html` background rgb(49,36,4) | Hero background (dark olive brown, with gold glow image `hero-glow.webp`) |
| #1A1509 | utility | Darkest brown surface |
| #524525 | utility | Olive brown mid tone |
| #986F21 | `--primary`, `--accent`, `--ring` = hsl(39 64% 36%) | Primary gold (buttons, links, rings) |
| #CBAA56 | utility (15 uses) | Gold text / borders |
| #D4B97A | utility | Light gold dividers, borders |
| #DCA93D / #F7CC53 | utility | Bright gold highlights |
| #EDE2CE | utility (109 uses) | Cream section background and borders |
| #F5F0E8 / #F5EDD9 / #FDFCF8 | utility | Off-white backgrounds |
| #E0DDD8 / #E8E6E1 / #EBEBEB | utility | Light grey borders |
| #002114 | `--secondary` = hsl(156 100% 6%) | Dark green: card headings (rgb 0,31,18), button text |
| #387246 / #2D5A3A | favicon dark bg, utility | Green accents |
| #0A0A0A | body color | Default text on light |
| #9B9690 / #9C9488 | utility | Muted warm grey text |
| #FFFFFF | button bg | White CTA on dark hero |

Type: Hedvig Letters Serif 400 for display (h1 88px / 96.8px, letter-spacing -2.2px, white), DM Sans variable for everything else (nav 16/400, h3 24/600 in #001F12, lede 28/400 at white 65%). Uppercase labels tracked .14em to .18em. Radius token `--radius: .5rem`; buttons 4px, cards 1rem / .75rem / 24px, pills 9999px. Logo: angular geometric "NAVA" caps wordmark plus an N monogram (two crossing diagonals) in a 40px rounded square (rx 6.67, 20% white). Favicon bg #D9D9D9 light, #387246 dark.

## 4. Typography (burgundy identity)

| Family | Weights used | Where | License | moji |
|---|---|---|---|---|
| **Muoto** (205TF) | 400 Regular, 500 Medium, 700 Bold. Files shipped: `MuotoTrial_Regular`, `MuotoTrial_Medium`, `MuotoTrial_Bold` .woff2 (trial builds). CSS family name `muoto`, `--font-muoto`. | All UI and headings. h1 80px / 80px line-height, letter-spacing -2.4px (-0.03em), 700. h2 56/56, -1.12px (-0.02em), 700. h3 20/26, 700. Body 18/23.4, +0.18px, 400. Nav 16/24, 400. Buttons 15px 700 +0.3px or 14px 500 +0.42px. Video frame 22 labels it "Headlines: Muoto Bold". | Commercial. Designed by Matthieu Cortat with Anthony Franklin and Sander Vermeulen (Base Design), released 2021 by 205TF (Lyon). Six weights Thin to Black with italics, plus Condensed, Ultra Condensed and Extended widths; variable. | `moji "Muoto"` finds one untrusted copy (github.com/tantaman/zero-presentations, muoto.ttf, license unknown). Not a legitimate source; do not use. |
| **Muoto Mono** (205TF) | Variable 400 to 700. File `MuotoMono_VAR_Trial.woff2`. CSS family `muotoMono`, `--font-muoto-mono`, class `.font-mono`. | Eyebrow labels ("HOW IT WORKS", "BACKED BY"), code-like chips `AGENT.PROPOSE()` `GUARDIAN.VERIFY()` `EXECUTE.APPROVED()`, table cells, input placeholders. Uppercase, tracked, small (12 to 13px). | Commercial (205TF). | `moji "Muoto Mono"`: no result. |

Fallback declared: `Arial, Helvetica, sans-serif` with size-adjust 105.28%.

Open alternatives (all OFL 1.1, all found trusted on fontsource via moji):
- For Muoto (neo-grotesque with soft, slightly organic curves, closed apertures, geometric round dots): **Instrument Sans** (closest overall feel at display sizes), **Schibsted Grotesk** (closer weight contrast for 700 headlines), **Onest** or **Figtree** (rounder, friendlier). Use Bold 700 for headlines with -0.03em tracking, Regular 400 body, Medium 500 small buttons.
- For Muoto Mono: **Geist Mono** (closest: tight, modern, good uppercase), or **JetBrains Mono**. Use uppercase with +0.1em to +0.2em tracking at 12 to 13px.
- Gold-site fonts for reference are both open: Hedvig Letters Serif and DM Sans (Google Fonts / fontsource, OFL).

## 5. Logo and mark

- Mark: two stacked "8"-like loops joined by one diagonal stroke, reading as a mirrored pair of double-rings or a stylised "N" drawn from two S-curves; also reads as a chain link / guardian knot. Monoline, uniform stroke, fully rounded terminals, roughly square footprint. Frame 19 shows the same monoline vocabulary extended into an icon set (magnifier, key, cherries/nodes, wallet, arrow-loop, twin rings).
- Wordmark: lowercase "nava" in a custom monoline geometric face matching the mark's stroke weight. Both "a" glyphs are drawn as mirrored open forms (a flipped, single-storey "a" that echoes the loops of the mark). Set tight, mark to the left at cap-height, gap about one letter width.
- Colorways seen: red mark + red wordmark on black (video open and close), black on red (flag, OG image), white on red (favicon/app icon), white on black (site header).
- Files: `screens/nava/rebrand-gallery-nava-logo-mark-512.png` (white mark on #FF0000 tile), `screens/nava/rebrand-gallery-og-nava-wordmark-on-red.jpg` (black lockup on #C8001A-ish red), `screens/nava/rebrand-video-frame-04.jpg` and `-32.jpg` (red lockup on black), `-10.jpg` (mark filled with the dotted texture).

## 6. Layout character (burgundy identity)

- Ground: true black page, single centered column, generous vertical rhythm (hero title sits at about 25% viewport height, sections separated by 160 to 200px).
- Radius: soft but not fully round. Cards and panels 16 to 26px; the hero "Nava Agent" panel about 24px; pills and CTAs fully rounded (34 to 54px on 40 to 44px height); small chips 7 to 10px; site radius list includes 6.25, 7, 9, 10, 14, 15, 16, 20, 24, 25, 26, 32, 34, 38 to 45px. Browser-frame mockups in the video use about 40px corners.
- Borders: 1px hairlines at white 5 to 19% (`color-mix(in oklab, white 15%, transparent)`), red keyline `#fe060066` on active items, `#ec0000` solid on badges. No drop shadows for depth; depth comes from inset highlights and red glow.
- Buttons: primary = vertical red gradient `#E60300 -> #AA0400`, white 700 15px label with +0.3px tracking, chevron icon right, `inset 0 2px 2px #ff5141` top highlight and `0 0 8px #fe0600` glow. Secondary = dark translucent pill (#0003 or #1e1e1ef0) with white label and a faint pink inset highlight (#db898975).
- Cards: `#0d0d0dcc` over a red-to-transparent gradient (`#fe060000 43.71% -> #fe06001a 100.86%`), 13 to 15px backdrop blur, hairline border. Comparison table uses alternating dark rows with red highlight row and check marks in red.
- Labels: mono, uppercase, tracked, 12 to 13px, either red (#FE0600 eyebrows) or white 65%.
- Imagery: no photography of people. One signature texture: a 3D field of red domes / scales lit from above (frame 07), used as the hero backdrop and inside the mark (frame 10) and inside a faceted gem/hexagon icon (frames 13, 25). Flags, signage and browser mockups carry the lockup. The "Backed by" logo strip runs as a marquee.
- Motion: slow, restrained. Marquee 15s linear infinite; ambient spin 50s linear; fade-in-up 0.5s ease-out with 1s stagger; hover opacity 0.3 to 0.35s ease-out. Video shows the mark rotating in 3D and dome texture parallax.
- Feel tags on rebrand.gallery: Futuristic, Modern, Dynamic, Intelligent. Style tags: UI, Abstract, Pattern, Shapes.

## 7. Screenshot index (relative to frontend/research/)

Burgundy identity (Nava Labs):
- `screens/nava/burgundy-site-navalabs-home-viewport.png` live navalabs.ai hero at 1440x900 (Sep 2026)
- `screens/nava/burgundy-site-navalabs-home-scrolled.png` "Propose. Verify. Execute." section
- `screens/nava/burgundy-site-navalabs-home-full.png` full page
- `screens/nava/rebrand-gallery-nava-logo-mark-512.png` mark, white on red (company logo on rebrand.gallery)
- `screens/nava/rebrand-gallery-og-nava-wordmark-on-red.jpg` OG image, black lockup on red
- `screens/nava/rebrand-video-wednesday-nava.mp4` the 33 s rebrand video (640x360, from cdn.rebrand.gallery)
- `screens/nava/rebrand-video-frame-01.jpg` to `-33.jpg` one frame per second. Key frames: 04 lockup red on black, 07 dome texture, 10 mark filled with texture, 13 gem icon, 16 flag, 19 icon set, 22 "Nava Verifies" Muoto Bold specimen, 25 developer card, 28 hero mockup with red gradient, 30 comparison table mockup, 32 closing lockup.

Gold site (nava.com, Kluisz.ai):
- `screens/nava/current-site-gold-navacom-home-viewport.png` hero at 1440x900
- `screens/nava/current-site-gold-navacom-home-scrolled.png` product section on cream
- `screens/nava/current-site-gold-navacom-home-full.png` full page
- `screens/nava/current-site-nava.svg` white NAVA wordmark + N tile
- `screens/nava/current-site-nava-icon-new.svg` favicon SVG (light/dark variants)
- `screens/nava/current-site-favicon-32.png`
- `screens/nava/current-site-hero-glow.webp` the gold glow hero background

Not captured: a pre-rebrand navalabs.ai screenshot (no archive exists), the Wayback copy of navalabs.ai as a screenshot (Vercel checkpoint blocks headless; the live capture above was taken with a stealth Chromium build instead).

## 8. Sources

- https://www.rebrand.gallery/rebrand/nava (RSC payload: brandColors, typeface "Muoto", agency Wednesday, vimeo id, feel/style tags, createdAt 2026-06-11)
- https://vimeo.com/1200404689 (oEmbed: "Nava Rebrand", Sahkyo, uploaded 2026-06-11)
- https://cdn.rebrand.gallery/rebrands/nava/nava.mp4
- https://navalabs.ai (live, Sep 2026) and its stylesheet `/_next/static/chunks/ee6d5314bd6ea2cb.css`
- https://web.archive.org/web/20260608111407/https://navalabs.ai/ (only capture; shows MuotoTrial fonts and "Guardrails for Autonomous Agents")
- Wayback CDX for nava.com (parked through 2026-03-15), kluisz.ai (Dec 2025 still Kluisz), navalabs.xyz (2024-09 to 2025-03)
- https://nava.com (live) and `/_next/static/chunks/0co57--0qnlug.css`, font name tables (Hedvig Letters Serif 24pt Regular, DM Sans 9pt)
- https://fortune.com/2026/04/14/nava-seed-funding-ai-financial-agents
- Globe and Mail / TipRanks, "Nava Emerges from Stealth With $8.3M Seed Round" (2026-08-17)
- https://www.linkedin.com/company/nava-ai-labs (posts 2026-04-21, 2026-06-15)
- https://www.crunchbase.com/organization/kluisz-ai (Nava aka Kluisz.ai, Bengaluru)
- https://www.typewolf.com/muoto and https://www.205.tf/muoto (designer, release, weights, widths)
- https://www.wednesdaystudio.co/ (agency; no public Nava case page found)
- moji CLI lookups (Muoto, Muoto Mono, Instrument Sans, Schibsted Grotesk, Figtree, Onest, Geist Mono, JetBrains Mono, Hedvig Letters Serif, DM Sans)

Searched with no result: Fonts In Use, Brand New (underconsideration), Behance and Dribbble had no Nava Labs / Wednesday case study as of 2026-09-18.

## 9. Unverified items

- Whether Nava Labs had any public visual identity before April 2026 (no archive; "rebrand" may in practice be the first public identity).
- Whether navalabs.xyz (captures 2024 to 2025) was this company.
- Exact launch date of the gold nava.com site (between 2026-03-15 and 2026-09-18).
- Whether the production site will move from Muoto Trial builds to licensed Muoto; the trial file names are a strong hint the license was not finalized when captured.
- The wordmark typeface: it appears custom-drawn to match the mark, not set in Muoto. Not confirmed by the agency.
- Video-sampled hexes (#E80000, #C80018, #900000) are compressed 640x360 frames and should be treated as approximate; use the CSS values.
- Wednesday Studio's own case study and any official brand guideline PDF were not found; the four gallery swatches are the only published brand colors.
