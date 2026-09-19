# Refero style reference: Galileo-ft

Source: https://styles.refero.design/style/10a77cbd-7847-4e1b-a09e-447ebad0f7c6
Captured: 2026-09-18. Refero page published 2026-05-07.
Refero metadata: theme `dark`, industry `fintech`. Refero does not assign a named style category (no "Editorial", "Brutalist", etc.). The closest recognised category is "Linear design" (dark-canvas SaaS aesthetic), covered in section 2b.

Note on the text below: the Refero description uses em dashes. This report replaces every em dash with a hyphen, otherwise the wording is unchanged.

---

## 1. Style name and verbatim description

**Name:** Galileo-ft

**Tagline:** deep-space command deck with electric blue signals

**Description (verbatim, em dashes replaced):**

> Galileo operates in a deep-space financial observatory: near-black navy canvases, whisper-thin type at display weights, and a single electric cobalt-blue accent that lights the interface like circuit current. Surfaces stack as dark on dark, separated by hairline lavender-tinted borders rather than elevation, giving the page a flat, architectural depth. The brand voice is restrained and premium - generous radii, oversized 3D glass sculpture photography as the hero motif, and color used sparingly so the blue accent always reads as intentional and high-stakes. Type is the signature: weight 100 headlines on a custom geometric face float above the page rather than commanding it, creating authority through restraint.

**Typographic voice (verbatim, em dashes replaced):**

> Plain is a custom geometric face used in an unusually thin register. Weight 100 at 42-147px is the brand's most aggressive differentiator: most fintech sites use weight 600-700 for headlines to project authority. Galileo's ultralthin weight projects authority through restraint - the type almost dissolves, which forces the surrounding negative space and the cobalt accent to carry the visual weight. The 0.25em tracked-out 10px eyebrow label is the counterpoint: tightly tracked large display paired with wide-tracked tiny caps creates a dramatic scale contrast. Body copy sits at weight 300 (Light) at 16px, one weight step lighter than typical - the whole system leans thin.

**Elevation (verbatim):**

> Galileo does not use drop shadows for elevation. Depth is achieved through hairline violet borders (#292f66, #4d5499), subtle surface color shifts between #03081a and #020626, and generous border-radius. This flat-architectural approach keeps the dark canvas clean and lets the vivid blue accent do the visual lifting.

**Do (verbatim list):**
- Use Plain Ultrathin weight 100 for all hero and section-level headlines at 42px or larger
- Use 48px border-radius for all buttons, nav pills, and floating action triggers
- Use 35px border-radius for all cards, panels, and content containers
- Use #3d50fc exclusively for primary filled actions and active states - never another color
- Use 0.25em letter-spacing (2.5px) on all 10px uppercase eyebrow labels
- Separate dark surfaces with 1px #292f66 hairlines, not drop shadows
- Pair the teal-to-cobalt gradient only with full-bleed banner surfaces, never inside cards

**Don't (verbatim list):**
- Never use weight 600 or 700 for headlines - the ultralthin register is the signature
- Never add drop shadows to cards or buttons - the system is flat by design
- Never use more than one vivid accent color per surface; cobalt and teal should not compete on the same element
- Never use solid underlines on links - use the 1px Quartz Lavender (#aab1f2) bottom border instead
- Never set body copy below weight 300 - the whole system is thin, but body must remain readable
- Never use sharp corners (0px or 4px radius) on interactive elements - all buttons, inputs, and cards use generous radii
- Never introduce a second dark-canvas color outside #03081a and #020626 - surface depth comes from the two-step shift between them

Tags on the page: none beyond `theme: dark` and `industry: fintech` in the page payload. SEO keywords in the payload: "Fintech design system", "Void Navy", "Deep Indigo", "Inkline Violet", "Quartz Lavender", "Times", "Plain", "Plain Light".

---

## 2. Example products

### 2a. Cited on the Refero page

- **Galileo Financial Technologies**, https://www.galileo-ft.com (the style's source). The domain now 301-redirects to https://tech.sofi.com/ with the banner "Galileo is now SoFi Tech Solutions". The captured design is the pre-rebrand site; the current SoFi Tech Solutions site keeps the same page structure (same headline "Expanding the financial frontier", same "FINANCIAL TECHNOLOGY PLATFORM" eyebrow, same solutions grid) but the visual treatment was not verified (tech.sofi.com returned 403 to headless fetch; only text was extracted).
- **Similar brands listed by Refero** (Refero's wording, em dashes replaced):
  - Mercury - Same dark-canvas fintech premium aesthetic with a single vivid accent color (Mercury uses violet) and thin geometric headlines
  - Ramp - Dark-mode financial platform with a single electric blue accent and ultralight display type floating on a near-black canvas
  - Modern Treasury - Deep navy dark theme with cobalt-blue primary actions and the same hairline-border card separation approach
  - Plaid - Developer-facing fintech with dark UI, monochromatic-violet palette, and abstract 3D illustration as the hero motif
  - Linear - Thin-weight display type, generous border-radius, and a single vivid accent color punching through a dark, quiet canvas
- **"More like this" grid on the page** (Refero neighbours, with Refero's taglines): AngelList (midnight greenhouse with violet), Column (deep navy ledger under cool dawn), Auros (abyssal terminal), Increase (institutional blueprint on vellum), Mercury (Alpine banking at blue hour), Astro (deep space mission control), Ameba (midnight control room), Home/fluidtouch (stargazer's dark observatory), Shares (ivory terminal with violet pulse), Join Parker, Shopify, Doppler (violet-lit vault at midnight), Origin Financial (midnight gallery of quiet wealth), iUSPC by Coinshift (midnight trading floor), GTE (trading terminal behind gallery), Clearbit, Duna, Twingate (midnight control room with violet), Cake Equity, Letter (private gallery with iridescent).

### 2b. Style category: "Linear design" (dark-canvas SaaS)

Refero names no category, but every trait it lists (near-black canvas, one vivid accent, hairline borders instead of shadows, thin display type, product screenshot as hero, restrained gradients) matches what the design press calls **Linear design** / **Linear style**, after linear.app.

Canonical definitions found:
- LogRocket, "Linear design: The SaaS design trend that's boring and bettering UI" (Daniel Schwarz, 2025-06): defines linear design as a straightforward, sequential layout, dark mode first, "visually, linear design is just flat design with dark mode and gradients". https://blog.logrocket.com/ux-design/linear-design
- LogRocket, "Which UI libraries/frameworks support the Linear aesthetic?" (2026-02): "Linear Design is a minimalist visual design aesthetic commonly seen on the websites of SaaS products"; Linear itself builds on Radix UI plus its own design system "Orbiter"; uses an 8px spacing scale. https://blog.logrocket.com/ux-design/linear-design-ui-libraries-design-kits-layout-grid
- Arlene Xu, "The rise of Linear style design" (Medium, 2023): "dark background with linear gradient colors, blurs, dynamic streamers, and micro-motion effects"; quotes Karri Saarinen on designing to look "professional" to engineers with Inter on black. Lists Linear, Raycast, Reflect, Twingate, SaaSUI as examples. https://medium.com/design-bootcamp/the-rise-of-linear-style-design-origins-trends-and-techniques-4fd96aab7646
- shadcn.io "Linear Design System" DESIGN.md: page floor #010102 ("never #000000 true black"), four-step surface ladder #0f1011 / #141516 / #18191a / #191a1b, hairlines #23252a to #3e3e44, single accent #5e6ad2, "surface lift and hairline borders carry every bit of hierarchy", Linear Display 12 to 80px at 400 to 600. https://shadcn.io/design/linear
- Linear, "How we redesigned the Linear UI (part II)" (2024-03): themes generated from opacities of black and white; Inter Display for headings, Inter for the rest; limited chroma in neutrals. https://linear.app/now/how-we-redesigned-the-linear-ui
- Refero's own Linear style page (canvas #08090a, card #0f1011 with 1px #23252a inset border and 12px radius, Inter 13 to 14px at weight 400 to 510). https://styles.refero.design/style/90ce5883-bb24-4466-93f7-801cd617b0d1

Live products to look at (well-known embodiments of the category):
1. Linear, https://linear.app (the namesake; dark canvas, one lavender accent, hairline cards)
2. Mercury, https://mercury.com (fintech, cited by Refero)
3. Ramp, https://ramp.com (fintech, cited by Refero)
4. Modern Treasury, https://www.moderntreasury.com (fintech, cited by Refero)
5. Raycast, https://www.raycast.com (cited by Medium and LogRocket as the second reference site of the style)
6. Vercel, https://vercel.com (cited by Refero's Linear page as the same dark-canvas, hairline-border approach)

Where Galileo-ft departs from stock Linear design: much larger radii (35 to 48px versus Linear's 6 to 12px), weight 100 display type instead of 400 to 600, a navy-tinted canvas instead of neutral charcoal, 3D glass renders instead of product screenshots as the hero, and heavy alternation between dark and near-white sections.

---

## 3. Visual character in detail

Sources for this section: Refero's token tables and component list, plus direct inspection of the hero screenshot and 14 frames of the 21-second scroll capture (see section 6).

### Color

Palette as published by Refero:

| Role | Name | Hex | Refero role text (shortened) |
|---|---|---|---|
| Canvas | Void Navy | #03081a | page background, base layer |
| Surface 1 | Deep Indigo | #020626 | cards, raised panels |
| Hairline | Inkline Violet | #292f66 | dividers, card borders, icon strokes |
| Border subtle | Dusk Iris | #4d5499 | muted borders, disabled states |
| Text tertiary | Mist Lilac | #7a83cc | tertiary text |
| Text secondary | Quartz Lavender | #aab1f2 | secondary text, link underlines, inactive nav |
| Light surface | Glacier White | #f5f6ff | light section backgrounds |
| Text primary | Pure White | #ffffff | headlines, primary text on dark |
| Primary accent | Pulse Cobalt | #3d50fc | filled actions, active states, brand signal |
| Secondary accent | Signal Teal | #05e0e0 | icons, tertiary links, gradient end, data viz |
| Decorative | Cyan Teal | #05cee0 | gradient origin |
| Gradient | Teal to Blue | linear-gradient(90deg, #05a1c9 0%, #3d50fc 100%) | announcement bar, full-bleed banners |
| Micro gradient | | #1e78f5 to #3d50fc | small UI accents |

Character:
- Dark, but not black: canvas and surface are navy-tinted (#03081a, #020626), only 1.05 to 1.06:1 against pure black. Neutrals are all hue-shifted toward blue-violet (lavender greys), so "grey" never appears; every neutral carries the brand hue.
- Low chroma overall, one high-chroma accent. Cobalt #3d50fc is highly saturated and used for fills, active tabs, and link colour. Teal is a second accent used as an outline colour and gradient endpoint, kept off surfaces that already carry cobalt.
- Contrast on dark: white text on #03081a is 19.9:1; lavender secondary #aab1f2 is 10.3:1; tertiary #7a83cc is 5.95:1; cobalt on the canvas is only about 3.7:1 (so cobalt is used as fill, with white text on it at 5.6:1, rather than as small text on dark).
- Observed in the frames: the live site alternates dark bands with near-white lavender-tinted bands (#f5f6ff-ish) far more than the Refero prose suggests. Large stats ("100+", "130M") are set in weight 100 with a cobalt-to-teal gradient text fill on the light band.
- Primary CTA on dark surfaces in practice is a white pill with cobalt text ("Let's Talk", "Login", "Learn More"). The cobalt-filled pill ("Contact Sales") appears on light surfaces. Refero's component list calls the cobalt fill the primary; the frames show both variants, chosen by surface.

### Typography

- Family: "Plain" (custom geometric grotesk) at weights 100, 300, 400. Refero substitutes: Inter (Thin / ExtraLight / Light), Neue Haas Grotesk Display Thin, Untitled Sans Light. A "Times" 400 at 16px was detected in the data but Refero flags it as not described (likely a fallback leak; see section 8).
- Scale (Refero calls it "Minor Third (1.2) from 14px base", though the published steps are not a strict 1.2 progression):

| Role | Size | Weight | Line height | Tracking |
|---|---|---|---|---|
| display | 147px | 100 | 0.8 | -2.94px (-0.02em) |
| heading-lg | 83px | 100 | 1.0 | -1.66px |
| heading | 56px | 100 | 1.1 | -1.12px |
| heading-sm | 42px | 100 | 1.1 to 1.2 | -0.84px |
| subheading | 28px | 100 | 1.3 | -0.56px |
| body | 16px | 300 (400 for emphasis) | 1.2 to 1.3 (1.8 in spacious paragraphs) | 0 |
| 14px | 14px | 300 | 1.4 to 1.8 | 0 |
| 13px | 13px | 300 | 1.2 | 0 |
| caption | 12px | 300 | 1.5 | 0 |
| eyebrow | 10px | 400 | 1.2 | +2.5px (0.25em), uppercase |
| 7px | 7px | 300 | 1.4 | 0 (legal / footnote scale) |

- Character: extreme weight contrast between hairline display type and regular-weight micro labels. Headlines at 56 to 83px, weight 100, tight leading (1.0 to 1.1), slightly negative tracking. Sentence case with a terminal full stop ("Expanding the financial frontier with banks."). Body copy is light (300) and generously leaded. Eyebrows are tiny, uppercase, widely tracked, often preceded by a small gradient glyph.
- Observed in frames: the body face on the live site reads as an Inter-like grotesk rather than the display face; large numerals share the weight 100 display treatment.

### Layout

- Density: "comfortable". Base unit 4px. Spacing scale 4 / 16 / 20 / 52 / 64 / 104 / 196. Section gap 64px, card padding 32px, element gap 9px, max width 1200px with 32 to 64px outer gutters.
- Hero: split layout, weight 100 headline left (about 45% width), oversized 3D glass sculpture right (about 40%), 40 to 80px between. Right-aligned vertical nav list with chevrons; "Login" as a white pill. Logo lockup top-left with 32px margin. After scroll the nav collapses to a single white circular hamburger button top-right.
- Sections alternate full-bleed dark bands and light bands. Band transitions use very large radii (roughly 200 to 300px corner sweeps) and even a full circle mask (frame 08), so the page reads as overlapping rounded plates rather than stacked rectangles.
- Cards: 35px radius, 1px hairline, no shadow. Dark card = #020626 on #03081a with #292f66 border. Light card = #ffffff with #7a83cc or #4d5499 border, dark text #020626.
- Radius set: tags 17px, cards 35px, inputs 35px, buttons 48px (pill). Raw extracted radii: 0.864px, 17.352px, 34.704px, 47.7px, 360px.
- Borders: 1px everywhere, colour-coded by prominence (#292f66 structural, #4d5499 subtle, #aab1f2 link underline, #ffffff ghost button).
- Shadows: none by rule. Observed exception: the floating "Talk With Gala" pill and dashboard mockups carry a soft ambient shadow in the frames.
- Whitespace: very generous; single-headline sections with 100 to 200px vertical padding; logo strip is a single centered row of 5 to 6 partner logos in lavender tint on dark.

### Components

- Primary filled button: #3d50fc fill, white text, 48px radius, 22px x 14px padding, weight 300 at 16px, no border, no shadow. Includes a trailing arrow glyph in the frames.
- Ghost outline button: transparent, 1px white border, white text, same geometry. Teal variant on dark sections: 1px #05e0e0 border with teal text ("Explore Our Platform", "Download the Fact Sheet").
- White pill (observed): #ffffff fill, cobalt text, 48px radius ("Let's Talk", "Login", "Learn More", "Watch Now").
- Pill nav link: transparent, 1px white or #aab1f2 border, 13 to 14px, weight 300 to 400.
- Tab pill: horizontal row inside a lavender-tinted rounded track; active tab #3d50fc fill with white 14px text, 17px radius; inactive tabs transparent with faint #4d5499 border; 9px gap.
- Eyebrow label: 10px, weight 400, uppercase, 2.5px tracking, #aab1f2 or #05e0e0, small gradient glyph at left.
- Outlined link: lavender text with a 1px #aab1f2 bottom border instead of an underline (Refero rule). Observed on light sections: cobalt text with a cobalt solid underline plus arrow ("Learn More ->", "Explore Cyberbank Core ->").
- Announcement bar: full-bleed teal-to-cobalt gradient, 14px white weight 300 text, white ghost "Learn More" pill, dismiss x at right.
- Floating chat trigger: #f5f6ff pill, 48px radius, avatar icon at left, weight 400 at 14 to 16px, fixed bottom-center on every screen.
- Dashboard / product screenshot: inside a 35px-radius, 1px-bordered card; the screenshot UI is dark with cobalt and teal data accents.
- Data table (observed, "Transaction History" in frame 10): dark navy card, uppercase tracked column headers in lavender (DATE, ACCOUNT ID, TYPE, METHOD, AMOUNT / POSITION, STATUS), light-weight body rows, faint alternating row bands, right-aligned ghost pills "Print" and "Export", and a teal-to-cobalt gradient range slider above the table. Status values as plain text (Pending, Cancelled, Complete, Not Confirmed), not coloured chips.
- Inputs: 35px radius per token table (no input observed in the frames).
- Stats block: weight 100 numerals at roughly 120px with gradient text fill, label in 24px light below, thin 1px dividers between the four cells.

### Imagery and iconography

- Hero motif: large 3D-rendered translucent cobalt-blue glass links / rings, glossy and refractive, blue-to-cyan gradient surfaces, no hard edges. Recurs at the footer CTA as a diagonal chain of glass discs.
- Otherwise minimal imagery: product dashboard mockups (light UI on dark, or dark UI in light sections), one office photo in the "Our people" section (Refero claims no people photography; the frames show one).
- Icons: outlined, 1.5 to 2px strokes in lavender or cobalt; small gradient glyphs as eyebrow markers; a white circular hamburger with cobalt lines.
- Logo: white crescent glyph plus lowercase "galileo" wordmark at about 20px, weight 300.

### Motion

- Refero has no motion notes. The scroll capture shows: standard scroll reveal (the nav collapses into a circular hamburger), a circular dark plate that scales in over a grey field with thin orbit arcs (frame 04 to 08), stat numerals counting up (83+ to 100+, 102M to 130M between frames 06 and 07). No looping animation was observed beyond the count-up.

---

## 4. Concrete CSS-level rules

Rules derived from the Refero tokens plus the observed site. Values are the Galileo-ft originals; the dark true-black variant is in section 5.

### Type scale suggestion

```css
:root {
  --font-display: "Plain", "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-body:    "Inter", ui-sans-serif, system-ui, sans-serif;

  /* display register: weight 100, tight leading, -0.02em */
  --text-display:    clamp(72px, 9vw, 147px); --leading-display: 0.85; --tracking-display: -0.02em;
  --text-heading-lg: clamp(48px, 6vw, 83px);  --leading-heading-lg: 1.0; --tracking-heading-lg: -0.02em;
  --text-heading:    56px; --leading-heading: 1.1;  --tracking-heading: -0.02em;
  --text-heading-sm: 42px; --leading-heading-sm: 1.1; --tracking-heading-sm: -0.02em;
  --text-subheading: 28px; --leading-subheading: 1.3; --tracking-subheading: -0.02em;

  /* reading register: weight 300 body, 400 emphasis */
  --text-body:    16px; --leading-body: 1.5;
  --text-sm:      14px; --leading-sm: 1.5;
  --text-caption: 12px; --leading-caption: 1.5;
  --text-eyebrow: 10px; --leading-eyebrow: 1.2; --tracking-eyebrow: 0.25em;

  --weight-thin: 100; --weight-light: 300; --weight-regular: 400;
}
h1, h2, .display { font-family: var(--font-display); font-weight: 100; }
body { font-family: var(--font-body); font-weight: 300; font-size: 16px; line-height: 1.5; }
strong, .emphasis { font-weight: 400; }
.eyebrow { font-size: 10px; font-weight: 400; letter-spacing: 0.25em; text-transform: uppercase; }
```

Notes: Refero's 1.2 line height on 16px body is too tight for paragraph copy; use 1.5 for body, keep 1.2 to 1.3 only for single-line UI labels. Below 42px, weight 100 loses legibility on most fonts; use 200 or 300 for 28px and smaller unless the chosen font has a hairline cut that holds up. Do not use weight 100 at any size below 28px. Never use 600 or 700 for headings in this style.

### Radius

```css
:root {
  --radius-tag:    17px;   /* chips, small pills, active tab */
  --radius-card:   35px;   /* cards, panels, inputs, screenshot frames */
  --radius-pill:   48px;   /* buttons, nav pills, floating triggers (effectively 9999px) */
  --radius-band:   200px;  /* section-band corner sweeps */
}
```
Nested radii: inner radius = outer radius minus padding (a 35px card with 16px inner padding gives 19px inner elements; Refero's 17px tag radius fits that).

### Borders

- 1px only. Never 2px structural borders.
- Three border tones: structural hairline (#292f66), subtle (#4d5499), and interactive/ghost (#aab1f2 or #ffffff).
- Links: `border-bottom: 1px solid currentColor` or the lavender tone; `text-decoration: none`.
- Cards: `border: 1px solid var(--border-hairline); background: var(--surface-1);` with no shadow.

### Shadows

- No. `box-shadow: none` on cards, buttons, tables, inputs. Hierarchy comes from the two-step surface shift plus hairlines.
- The single permitted exception: a fixed floating trigger (chat pill) may carry one soft ambient shadow, `0 8px 24px rgb(0 0 0 / 0.35)`, because it floats over changing backgrounds.

### Spacing rhythm

```css
:root {
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px; --space-5: 20px;
  --space-6: 24px; --space-8: 32px; --space-13: 52px; --space-16: 64px; --space-26: 104px; --space-49: 196px;
  --gap-element: 8px;     /* Refero says 9px; round to the 4px grid */
  --pad-card: 32px;
  --gap-section: 64px;
  --pad-section: 104px;   /* top and bottom of full-bleed bands */
  --max-width: 1200px;
  --gutter: clamp(24px, 4vw, 64px);
}
.button { padding: 14px 22px; border-radius: var(--radius-pill); font-weight: 300; font-size: 16px; }
.tab    { padding: 14px 22px; border-radius: var(--radius-tag); font-weight: 400; font-size: 14px; }
```

### Tables and dense data in this style

The Galileo-ft style is a marketing surface; its only observed table is the "Transaction History" mockup. To keep dense operational data (a call log, a bookings diary) in character:

- Container: one card, `border-radius: 35px` on the outer frame only (or 17px if the table is the whole viewport), 1px hairline, no shadow. Inside the card, rows are separated by 1px hairlines, not cells with borders.
- Header row: 10 to 11px uppercase, weight 400, 0.15 to 0.25em tracking, secondary text colour. No background fill on the header.
- Body rows: 13 to 14px, weight 300 for text and weight 400 for the key column; `font-variant-numeric: tabular-nums` on numeric and time columns; row height 36 to 40px; cell padding 10px 16px.
- Row striping: optional very faint band (surface-1 on canvas) as observed; hover raises to surface-1.
- Status: plain text in secondary colour, not filled chips. If a chip is unavoidable, use a 17px-radius outline chip with a 1px hairline and no fill.
- Actions: ghost pills, 1px border, 13px, right-aligned in the toolbar; one cobalt filled pill at most per toolbar.
- Selection / active row: 1px cobalt left rule or cobalt text on the key cell, not a full-row fill.
- Numbers that matter (counts, totals) get the display treatment: weight 100, 40 to 72px, tight leading, on their own stat cell with 1px dividers between cells.
- Keep density high but airy: 4px grid, 12 to 16px horizontal padding, 1px separators; no zebra stripes at full contrast, no heavy header bars, no card-in-card nesting.

### Gradients

- Use a gradient only on a full-bleed band or as text fill on hero numerals. Never inside a card. Always horizontal (90deg), always terminating in the primary accent.

### Components summary

| Component | Rule |
|---|---|
| Primary button | accent fill, white text, pill, 14px x 22px, weight 300, no border, no shadow |
| Secondary button | transparent, 1px border in text colour, pill |
| Inverted button on dark | white fill, accent text, pill (observed pattern) |
| Tab | 17px radius, active = accent fill; inactive = 1px subtle border |
| Card | surface-1, 1px hairline, 35px, 32px padding |
| Input | surface-1, 1px hairline, 35px, 14px x 20px padding, weight 300 |
| Link | no underline, 1px bottom border |
| Eyebrow | 10px caps, 0.25em tracking, secondary colour |
| Divider | 1px hairline |
| Nav | right-aligned vertical list on large screens, collapses to a single circular button |

---

## 5. Dark true-black adaptation (#000 canvas, white text, burgundy accent)

Standing constraints for the project: #000 background, white primary text, dense information, no decorative card or pill chrome, no light grey subtitle lines above sections, no continuously repainting animation. The brand palette is a burgundy from another source (hex not yet fixed). The notes below keep what makes Galileo-ft recognisable and drop what conflicts.

### What transfers directly

- Flat, shadowless hierarchy built from a two-step surface shift plus 1px hairlines. This is the core of the style and it works better on #000 than on navy.
- Weight 100 to 200 display type with tight leading and -0.02em tracking for headlines and big numerals; weight 300 body, weight 400 emphasis; 10px tracked uppercase eyebrows.
- One saturated accent used scarcely: fills on the single primary action, the active tab, the selected row marker, key icons. Everything else stays white, grey, or hairline.
- 1px bottom-border links instead of underlines.
- Tabular, hairline-separated data with uppercase tracked headers.

### What changes

- **Canvas and surfaces.** Replace #03081a / #020626 with #000000 / #0a0a0a (or #0d0d0d). The two-step shift stays two steps. Do not add a third dark surface. Do not tint the neutrals blue; if you tint, tint toward the burgundy (warm grey / rose grey) so the whole system carries the brand hue the way Galileo's lavender greys carry cobalt.
- **Hairlines.** #292f66 becomes #1f1f1f (structural, 1.3:1 against black) and #2e2e2e (subtle). A brand-tinted hairline #3a1622 (1.32:1) works for card borders if you want warmth without chroma in the text.
- **Text ladder.** Primary #ffffff (21:1). Secondary: a warm grey such as #b8a9ad (9.3:1) or rose grey #c9b3ba (10.6:1), replacing lavender #aab1f2. Tertiary: #8a7f83 or similar around 5:1. Avoid the "light grey subtitle line above sections" pattern entirely; eyebrows are allowed only when they carry information (a category, a status), not as decoration.
- **Radii.** Galileo's 35 to 48px radii are marketing chrome. For a dense operational UI on black, cut them: 6 to 8px on cards and inputs, 9999px only on genuinely pill-shaped controls (a single primary button, tabs), 0 to 4px inside tables. Keep the "no sharp corners on interactive elements" spirit at 6px, not 35px. The band-corner sweeps do not transfer.
- **Cards.** Prefer hairline-separated regions over cards. Where a bounded panel is needed: #0a0a0a fill, 1px #1f1f1f border, 6 to 8px radius, no shadow. No card-in-card.
- **Gradients.** Drop the teal-to-cobalt banner. If a gradient is wanted at all, use it once, as text fill on a hero numeral, burgundy to rose, never on a surface.
- **Imagery.** No 3D glass renders. The "product is the visual" principle transfers: live call state, transcripts, and diaries are the imagery.
- **Motion.** Count-ups and scroll reveals are fine as one-shot 150 to 300ms transitions with the project easing. No looping pulses, shimmer, or spinners.

### Hosting a burgundy accent on black

Contrast figures (WCAG, computed):

| Candidate | Hex | vs #000 | white text on it |
|---|---|---|---|
| classic burgundy | #800020 | 1.94 | 10.83 |
| wine | #722F37 | 2.18 | 9.65 |
| deep maroon | #5C0A1E | 1.52 | 13.84 |
| raspberry burgundy | #A3264F | 2.95 | 7.12 |
| bright burgundy | #B3244E | 3.28 | 6.40 |
| rose (lifted accent) | #E05A7A | 5.91 | 3.55 |
| pale rose (accent text) | #F2B8C6 | 12.45 | 1.69 |
| Galileo cobalt, for reference | #3d50fc | 3.75 | 5.60 |

Implications:
- A true burgundy (#800020 and darker) is nearly invisible as text or thin strokes on #000 (under 2:1). It must be used as a **fill** with white text on it (10:1 or better), exactly how Galileo uses cobalt: filled primary button, active tab fill, selected-row fill. This matches the style's rule "accent exclusively for primary filled actions and active states".
- For accent **text**, icons, 1px focus rings, and link borders on black, derive a lifted tone of the same hue at 4.5:1 or better (about #E05A7A or lighter for the target burgundy; adjust hue to match the source brand). Keep the two tones as a pair: `--accent-fill` (deep) and `--accent-ink` (lifted). This is the one deliberate addition over Galileo's single-tone accent, forced by the black canvas.
- A burgundy-tinted dark surface (#140609 or so) can replace #0a0a0a for the "surface-1" step if the brand needs more warmth; keep it under 1.15:1 against black so it reads as a shift, not a colour.
- Never put burgundy and a second saturated colour on the same surface (Galileo's cobalt/teal rule). Status semantics (error, warning) should use text weight and hairlines, or a single desaturated tone, so the burgundy stays the only chroma.
- Sparse deployment is what makes it read as intentional: one filled accent element per view, the active state, and the selection marker. Everything else is white on black with hairlines.

### Token sketch

```css
:root {
  --bg: #000000;
  --surface-1: #0a0a0a;           /* or #140609 for a brand-warm step */
  --border-hairline: #1f1f1f;     /* or #3a1622 brand-tinted */
  --border-subtle: #2e2e2e;
  --text: #ffffff;
  --text-2: #c9b3ba;              /* rose grey, 10.6:1 */
  --text-3: #8a7f83;              /* about 5:1 */
  --accent-fill: #800020;         /* replace with the source burgundy */
  --accent-fill-text: #ffffff;    /* 10.8:1 on #800020 */
  --accent-ink: #E05A7A;          /* lifted tone for text, icons, rings, 5.9:1 on black */
  --radius-control: 6px;
  --radius-pill: 9999px;
  --radius-panel: 8px;
  --hairline: 1px solid var(--border-hairline);
  --ease: cubic-bezier(0.175, 0.885, 0.32, 1.1);
  --dur-state: 150ms; --dur-popover: 200ms; --dur-overlay: 300ms;
}
body { background: var(--bg); color: var(--text); font-weight: 300; }
h1 { font-weight: 100; letter-spacing: -0.02em; line-height: 1.0; }
.button-primary { background: var(--accent-fill); color: var(--accent-fill-text); border-radius: var(--radius-pill); border: 0; box-shadow: none; }
.button-ghost   { background: transparent; color: var(--text); border: 1px solid var(--border-subtle); border-radius: var(--radius-pill); }
a { color: inherit; text-decoration: none; border-bottom: 1px solid var(--accent-ink); }
.row-selected   { box-shadow: inset 2px 0 0 var(--accent-fill); }  /* left rule, no fill */
table th { font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; font-weight: 400; color: var(--text-2); }
table td { font-size: 13px; font-weight: 300; font-variant-numeric: tabular-nums; border-top: var(--hairline); padding: 10px 12px; }
```

---

## 6. Screenshot index

All paths relative to `frontend/research/`. Folder: `screens/refero/`.

Refero page captures (Playwright Chromium 1223, viewport 1440 wide; the page uses an inner scroll pane, so it was captured at a 9600px viewport with the "Show all 11 steps" and "Show all 5 fonts" toggles expanded):

| File | Size | Content |
|---|---|---|
| screens/refero/01-full-page.png | 1440 x 9600 | Entire Refero style page, left pane (preview, palette, type scale, fonts, spacing, radius, guidelines, "More like this") and right pane (DESIGN.md export) |
| screens/refero/03-section-01.png | 1440 x 1600 | Header, hero preview, name, tagline, description, Brand and Accent swatches; right: DESIGN.md colour and typography tokens |
| screens/refero/03-section-02.png | 1440 x 1600 | Neutral swatches, full 11-step type scale with specimens; right: type scale table, spacing, radius, layout, first components |
| screens/refero/03-section-03.png | 1440 x 1600 | All 5 font entries (Times, Plain, Plain Light, Plain Ultralight, Plain Ultrathin); right: components, Do and Don't, surfaces, elevation |
| screens/refero/03-section-04.png | 1440 x 1600 | Spacing table, border radius table, Guidelines Do and Don't; right: layout, agent prompt guide, gradient system, similar brands, CSS custom properties |
| screens/refero/03-section-05.png | 1440 x 1600 | "More like this" grid part 1 (AngelList, Column, Auros, Increase, Mercury, Astro, Ameba, Home, Shares, Join Parker); right: CSS variables continued |
| screens/refero/03-section-06.png | 1440 x 1600 | "More like this" grid part 2 (Shopify, Doppler, Origin Financial, iUSPC, GTE, Clearbit, Duna, Twingate, Cake Equity, Letter); right: Tailwind v4 theme |

Example images downloaded from Refero's CDN (the Galileo-ft site itself):

| File | Size | Content |
|---|---|---|
| screens/refero/example-00-cover.jpg | 1440 x 900 | Refero cover image: Galileo hero at 1440 |
| screens/refero/example-01-hero-screenshot.jpg | 1600 x 1000 | Hero screenshot / video poster: announcement gradient bar, weight 100 headline, glass sculpture, right vertical nav, "Talk With Gala" pill |
| screens/refero/example-02-favicon.png | 256 x 256 | Galileo crescent glyph in cobalt |
| screens/refero/example-scroll-01.png to -14.png | 1600 x 1000 each | Frames every 1.5s from Refero's 21s scroll capture (mp4 `3001ccdb-d5ad-4585-98c3-485f42b92019`): 01 hero; 02 partner logo strip on dark; 03 "One platform, endless solutions" with dashboard mockup, eyebrow, teal ghost button; 04 and 08 dark circular plate "Galileo named Best-in-Class" with orbit arcs; 05 same section; 06 and 07 "Galileo at a glance" stats with gradient weight 100 numerals (count-up mid-state); 09 solutions grid on light with cobalt underlined links and pill tab bar; 10 "One platform, tailored experiences" with Transaction History dark table card, cobalt filled CTA, gradient band start; 11 and 12 gradient band end and dark video card with logo; 13 and 14 footer CTA with diagonal glass discs, cobalt filled pill, teal ghost pill, large band radius |

Not saved: the "More like this" thumbnails for other brands (out of scope) and the raw 4.2 MB mp4 (kept in the session scratchpad only).

---

## 7. Sources

- Refero style page (primary): https://styles.refero.design/style/10a77cbd-7847-4e1b-a09e-447ebad0f7c6 (text via octen extract and WebFetch; page HTML via curl; screenshots via agent-browser)
- Refero CDN media: https://images.refero.design/styles/refero.design/image/24035982-add1-4ce8-a8ef-00ca76d8d945.jpg, .../cb1af2b6-896e-4b2b-8382-72899a32bb22.jpg, .../871401cb-102a-468d-8c7c-c4cb1d4b9d2b.png, https://images.refero.design/styles/refero.design/video/3001ccdb-d5ad-4585-98c3-485f42b92019.mp4
- Galileo source site: https://www.galileo-ft.com (301 to https://tech.sofi.com/, text extracted via octen)
- LogRocket, Linear design definition: https://blog.logrocket.com/ux-design/linear-design
- LogRocket, Linear aesthetic libraries and grid: https://blog.logrocket.com/ux-design/linear-design-ui-libraries-design-kits-layout-grid
- Arlene Xu, The rise of Linear style design: https://medium.com/design-bootcamp/the-rise-of-linear-style-design-origins-trends-and-techniques-4fd96aab7646
- shadcn.io Linear DESIGN.md: https://shadcn.io/design/linear
- Linear, How we redesigned the Linear UI (part II): https://linear.app/now/how-we-redesigned-the-linear-ui
- Refero Linear style page: https://styles.refero.design/style/90ce5883-bb24-4466-93f7-801cd617b0d1
- Contrast ratios: computed locally with the WCAG 2.x relative luminance formula.

---

## 8. Unverified

- Refero's token and component text is AI-generated from extracted CSS ("detected in extracted data but not described by AI" appears for Times). The "Times 400 at 16px" entry is most likely a fallback font leak in the extraction, not a design choice; the live site shows no serif.
- Several Refero "Don't" rules are contradicted by the captured site: solid cobalt underlines appear on light-section links; a photo of people appears in "Our people"; the floating chat pill carries a shadow; the Refero prose says "dark on dark" while the site alternates dark and near-white bands about equally. Treat Refero's rules as a stylised summary, not a spec.
- The "Minor Third (1.2) from 14px base" label does not match the published steps (10, 12, 13, 14, 16, 28, 42, 56, 83, 147); the steps look extracted, not generated from a ratio.
- Exact font identity ("Plain") was not confirmed against the site's CSS (galileo-ft.com now redirects and tech.sofi.com blocks headless fetch with 403). The hero face is visibly a thin geometric grotesk consistent with Optimo's Plain; body face looks Inter-like.
- Whether the current SoFi Tech Solutions site still uses this visual system was not verified beyond page text.
- Current live appearance of Mercury, Ramp, Modern Treasury, Plaid, Raycast, and Vercel was not re-checked on 2026-09-18; they are listed on the strength of Refero's and the cited articles' descriptions. Refero's own Mercury page tagline ("Alpine banking at blue hour") suggests Mercury's current site is photography-led rather than flat dark.
- Refero's "Design Tokens" export tab could not be opened in the headless session (a sticky header covered the tab); its content was not captured. DESIGN.md, CSS Variables, and Tailwind v4 exports were captured and agree with each other.
- The burgundy hex is a placeholder set (#800020 and neighbours). Recompute contrast once the real brand value arrives; the fill-versus-ink two-tone recommendation holds for any hue whose deep tone falls under 3:1 on black.
