# ROSARIO design

Style reference supplied by Marcos on 18 Sep 2026 (Refero Galileo-ft recolored to Nava). This file is the visual contract; `tokens/tokens.css` implements it and the design linter enforces it. The console screens, event contract and component mapping live in `CONSOLE.md`.

Override (Marcos, 19 Sep): the page canvas is **Inkline Crimson #2d1012**, not Nava Black. Cards keep Obsidian Burgundy #14090a (a step darker than the canvas), hairlines move to Dusk Maroon #5e1f25, subtle borders to Muted Coral #a86d70. Black remains for the deepest plates and imagery grounds (`--canvas-deep`). Wherever the reference text below says black canvas, read crimson. Second override (19 Sep, accessibility): filled controls (primary button, active tab) use Nava Fire #bc0400 because white on Nava Red is 4.0:1; Nava Red remains the brand ink for icons, active states and the mark. There is no announcement bar (Marcos, 19 Sep): the header is one row on every page, lockup left, section nav and the console button right, and the hero sits below it. Small tiles under 200px (mark gallery, swatches) take the 17px tag radius; the 35px card radius applies from panel size up. Eyebrows: no eyebrow labels anywhere on the brand pages or the console (Marcos, 19 Sep); sections open with the headline. Copy: the event has no phone number (the harness and the jury connect over a socket), so the landing page never shows a dialable number; the Talk section points at the web call that ships with the console. Motion: the 150 to 300ms tokens govern UI state changes; the brand page's one-shot entrances and scroll-scrubbed motion (`brand/motion.js`) run 450 to 1200ms on purpose, never loop, and collapse to opacity under reduced motion. Atmosphere (Marcos, 19 Sep): the page sits on two WebGL fields taken from React Bits (MIT + Commons Clause), recoloured to this palette and ported to plain WebGL2 in `brand/waves.js`. Gradient Waves covers the top 1100px behind the hero and fades out; Grainient runs the full viewport underneath it at 60% opacity. Both are drawn once and then only while the reader scrolls, so nothing loops and nothing repaints at rest; under reduced motion each is a single still frame. There is no dot texture and no section washes. The crimson page colour lives on `html` (a background on `body` would paint over the canvases). Where the reference below says Nava Red for filled controls or a gradient announcement background, the overrides in this paragraph win.

Dashboard override (19 Sep, product pass): the primary navigation is Overview, Calls, Calendar and Settings in a fixed-width sidebar and four-item mobile bar. Active calls appear above history in Calls. Cases and the voice demo are separate tools. No decorative dots, stage beads, chips or left-side selection stripes. This supersedes the earlier dot-texture atmosphere clause; section washes remain. Selection uses one neutral surface that moves between controls in 350ms. Caller and ROSARIO messages use opposite-aligned chat bubbles; playback reveals turns at detected speech endings, while pausing or scrolling restores the full conversation.

The dashboard supports dark and light themes through semantic tokens. Light uses warm paper `#f7f3ef`, white surfaces and burgundy `#2d1012` text. Its muted text is `#75565a`; dark metadata uses `#bb8688` to remain readable over row hover fills. Theme choice persists under `rosario-theme`. The 500ms circular reveal is adapted from [Magic UI's Animated Theme Toggler](https://magicui.design/docs/components/animated-theme-toggler), with its MIT license in `licenses/magic-ui.txt`. Reduced motion switches instantly. Navigation and chat reveal durations also collapse; no decorative animation loops were added.

Text selection uses `--selection-bg`: Dusk Maroon in dark mode and rose `#e4c9cd` in light mode, with the theme's foreground color. Icons use [Phosphor React](https://github.com/phosphor-icons/react), regular weight, imported per icon. Its rounded geometry suits the light typography without adding visual weight.

The landing page's “Sign in” links and ROSARIO logos open Overview (`/metrics`), not an authentication flow. Above 1100px the bottom-center link stays available unless the header or footer “Sign in” link is visible; unrelated section actions do not hide it. Narrower layouts use the header and footer links. Preview tables fit their cards and stack their rows on small screens. They scroll with the page, with no nested scrollbar for row entrance animations.

Settings uses idle orb portraits for the Rosario, Clara and Serena presets. Clara's blue and Serena's sage palettes are artwork-only `--voice-*` tokens; controls retain the shared clinic colors. Preset changes use an interruptible 200ms GSAP transition, skipped for keyboard input and reduced motion. Tool markers form compact stacks above the audiogram and spread horizontally on hover. Their lane never changes height; reduced motion exposes all markers without a spatial transition.

---

# Galileo-ft - Style Reference
> obsidian command deck with electric nava red signals

**Theme:** dark

Galileo operates in an obsidian financial observatory: true-black canvases, whisper-thin type at display weights, and a single electric Nava Red accent that lights the interface like circuit current. Surfaces stack as dark on dark, separated by hairline crimson borders rather than elevation, giving the page a flat, architectural depth. The brand voice is restrained and premium - generous radii, oversized 3D generative ribbon and glass sculpture photography as the hero motif, and color used sparingly so the red accent always reads as intentional and high-stakes. Type is the signature: weight 100 headlines on a custom geometric face float above the page rather than commanding it, creating authority through restraint.

## Tokens - Colors

| Name | Value | Token | Role |
|------|-------|-------|------|
| Nava Black | `#000000` | `--color-nava-black` | Page canvas and primary dark surface - the base layer everything else floats on |
| Obsidian Burgundy | `#14090a` | `--color-obsidian-burgundy` | Card surfaces, raised panels, and secondary structural fills |
| Inkline Crimson | `#2d1012` | `--color-inkline-crimson` | Hairline dividers, card borders, icon strokes - the structural skeleton color |
| Ash Rose | `#d4a5a5` | `--color-ash-rose` | Secondary text, outlined link borders, muted body copy, inactive navigation |
| Muted Coral | `#a86d70` | `--color-muted-coral` | Tertiary text and supporting UI elements needing softer contrast |
| Dusk Maroon | `#5e1f25` | `--color-dusk-maroon` | Muted borders, disabled states, low-priority card outlines |
| Nava White | `#fefefe` | `--color-nava-white` | Light-theme card surfaces, light section backgrounds, high-contrast text on dark |
| Pure White | `#ffffff` | `--color-pure-white` | Primary headlines, primary text on dark, nav and button borders |
| Nava Red | `#fe0600` | `--color-nava-red` | Primary action buttons, active states, key icons, brand signal - the single vivid accent that powers the entire interface |
| Nava Fire | `#bc0400` | `--color-nava-fire` | Secondary accent for icons, tertiary links, gradient terminal, and data-viz highlights |
| Ember Glow | `#e62800` | `--color-ember-glow` | Decorative gradient origin and atmospheric illustration accent |
| Gradient Fire-Red | `linear-gradient(90deg, rgb(188, 4, 0) 0%, rgb(254, 6, 0) 100%)` | `--color-gradient-fire-red` | Hero gradient banner, brand transition washes - Fire flowing into Red creates a continuous energy signal |

## Tokens - Typography

### Times - Times - detected in extracted data but not described by AI · `--font-times`
- **Weights:** 400
- **Sizes:** 16px
- **Line height:** 1.2
- **Role:** Times - detected in extracted data but not described by AI

### Plain - Primary interface typeface. Weight 100 for large display and heading sizes (42–147px), weight 300 for body, weight 400 for emphasized inline text. The ultrathin weights are the defining signature - no other fintech brand runs 100-weight at this scale. Substitute: Inter (light/extra-light), Neue Haas Grotesk Display Thin, or Untitled Sans Light. · `--font-plain`
- **Substitute:** Inter, Neue Haas Grotesk Display Thin, Untitled Sans Light
- **Weights:** 100, 300, 400
- **Sizes:** 10px, 13px, 14px, 16px
- **Line height:** 1.20, 1.30
- **Letter spacing:** 0.2500em at 10px (tracked eyebrow/label style), normal at body sizes
- **Role:** Primary interface typeface. Weight 100 for large display and heading sizes (42–147px), weight 300 for body, weight 400 for emphasized inline text. The ultrathin weights are the defining signature - no other fintech brand runs 100-weight at this scale. Substitute: Inter (light/extra-light), Neue Haas Grotesk Display Thin, or Untitled Sans Light.

### Plain Light - Long-form body copy, description paragraphs, and card detail text. Weight 300 keeps long passages airy and scannable against the dark canvas. The 1.80 line-height variant is used for spacious paragraph blocks. Substitute: Inter Light, Untitled Sans Light. · `--font-plain-light`
- **Substitute:** Inter Light, Untitled Sans Light
- **Weights:** 300
- **Sizes:** 12px, 14px
- **Line height:** 1.40, 1.50, 1.80
- **Letter spacing:** normal
- **Role:** Long-form body copy, description paragraphs, and card detail text. Weight 300 keeps long passages airy and scannable against the dark canvas. The 1.80 line-height variant is used for spacious paragraph blocks. Substitute: Inter Light, Untitled Sans Light.

### Plain Ultralight - Subheadings, section headers within cards, and product category labels. Weight 100 at 28px stays in the same whisper register as the display sizes but at a scannable mid-scale. Substitute: Inter ExtraLight, Neue Haas Grotesk Display Thin. · `--font-plain-ultralight`
- **Substitute:** Inter ExtraLight, Neue Haas Grotesk Display Thin
- **Weights:** 100
- **Sizes:** 28px
- **Line height:** 1.30
- **Letter spacing:** -0.56px (-0.02em)
- **Role:** Subheadings, section headers within cards, and product category labels. Weight 100 at 28px stays in the same whisper register as the display sizes but at a scannable mid-scale. Substitute: Inter ExtraLight, Neue Haas Grotesk Display Thin.

### Plain Ultrathin - Hero headlines, display text, and section-leading titles. Weight 100 at 147px is the brand most extreme typographic move - the characters nearly dissolve into hairlines, which is why the vivid red accent and surrounding negative space carry so much of the visual weight. Substitute: Inter Thin, Neue Haas Grotesk Display Thin. · `--font-plain-ultrathin`
- **Substitute:** Inter Thin, Neue Haas Grotesk Display Thin
- **Weights:** 100
- **Sizes:** 42px, 56px, 83px, 147px
- **Line height:** 0.80, 1.00, 1.10, 1.20
- **Letter spacing:** -0.84px at 42px, -1.12px at 56px, -1.66px at 83px, -2.94px at 147px (all -0.02em)
- **Role:** Hero headlines, display text, and section-leading titles. Weight 100 at 147px is the brand most extreme typographic move - the characters nearly dissolve into hairlines, which is why the vivid red accent and surrounding negative space carry so much of the visual weight. Substitute: Inter Thin, Neue Haas Grotesk Display Thin.

### Type Scale

| Role | Size | Line Height | Letter Spacing | Token |
|------|------|-------------|----------------|-------|
| eyebrow | 10px | 1.2 | 2.5px | `--text-eyebrow` |
| caption | 12px | 1.5 | - | `--text-caption` |
| body | 16px | 1.3 | - | `--text-body` |
| subheading | 28px | 1.3 | -0.56px | `--text-subheading` |
| heading-sm | 42px | 1.1 | -0.84px | `--text-heading-sm` |
| heading | 56px | 1.1 | -1.12px | `--text-heading` |
| heading-lg | 83px | 1 | -1.66px | `--text-heading-lg` |
| display | 147px | 0.8 | -2.94px | `--text-display` |

## Tokens - Spacing & Shapes

**Base unit:** 4px

**Density:** comfortable

### Spacing Scale

| Name | Value | Token |
|------|-------|-------|
| 4 | 4px | `--spacing-4` |
| 16 | 16px | `--spacing-16` |
| 20 | 20px | `--spacing-20` |
| 52 | 52px | `--spacing-52` |
| 64 | 64px | `--spacing-64` |
| 104 | 104px | `--spacing-104` |
| 196 | 196px | `--spacing-196` |

### Border Radius

| Element | Value |
|---------|-------|
| tags | 17px |
| cards | 35px |
| inputs | 35px |
| buttons | 48px |

### Layout

- **Page max-width:** 1200px
- **Section gap:** 64px
- **Card padding:** 32px
- **Element gap:** 9px

## Components

### Primary Filled Button
**Role:** Main call-to-action - used for the highest-priority conversion on each surface

Nava Red (#fe0600) fill, Pure White text, 48px border-radius (pill-shaped), 22px horizontal padding × 14px vertical padding. Plain weight 300 at 16px, letter-spacing normal. No shadow, no border. The saturated red against the deep black creates a high-voltage focal point without needing elevation.

### Ghost Outline Button
**Role:** Secondary action - paired beside primary CTAs to offer an alternative path

Transparent background, 1px Pure White border (#ffffff), Pure White text, 48px border-radius, 22px × 14px padding. Plain weight 300 at 16px. Used for actions like 'Learn More' in the announcement bar and navigation-level secondary actions.

### Pill Navigation Link
**Role:** Right-side utility nav items and floating action triggers

Transparent fill, 1px border in Pure White or Ash Rose (#d4a5a5), white or ash rose text, 48px border-radius. 13–14px Plain weight 300–400. The ash rose border variant signals a non-primary or secondary nav position.

### Dark Card
**Role:** Feature card, product tile, and content block container on dark sections

Obsidian Burgundy (#14090a) background, 1px Inkline Crimson (#2d1012) border, 35px border-radius, 32px padding. No drop shadow. Cards rely on the crimson hairline border and subtle background shift rather than elevation to separate from the void canvas.

### Light Card
**Role:** Content card used on light/white sections of the page

Pure White (#ffffff) background, 1px Muted Coral (#a86d70) or Dusk Maroon (#5e1f25) border, 35px border-radius, 32px padding. Contains dashboard screenshots, product mockups, and tabbed content panels. Dark text (#14090a) inside.

### Tab Pill
**Role:** Active category selector inside product navigation bars

Nava Red (#fe0600) fill for the active tab, white text, 17px border-radius (smaller pill than buttons), 22px × 14px padding. Inactive tabs are transparent with a faint crimson border (#5e1f25). 14px Plain weight 400.

### Eyebrow Label
**Role:** Small section-prelude text above headings - e.g. 'FINANCIAL TECHNOLOGY PLATFORM'

Plain weight 400 at 10px with 0.25em letter-spacing (2.5px), uppercase, Ash Rose (#d4a5a5) or Nava Fire (#bc0400) color. Functions as a tracked-out category tag that frames the weight-100 heading below it.

### Outlined Link
**Role:** Inline 'Explore →' and 'Learn more' style links within body copy

No background, Ash Rose (#d4a5a5) 1px bottom border acting as the link underline, ash rose text, Plain weight 300 at 16px. The thin ash rose rule replaces the traditional solid underline for a lighter, architectural feel.

### Floating Chat Trigger
**Role:** Persistent 'Talk With Gala' conversation launcher

Nava White (#fefefe) pill-shaped background, 48px border-radius, 1px light border, small avatar icon at left, Plain weight 400 at 14–16px. Floats fixed at bottom-center on all screens. Represents the brand always-on customer engagement.

### Announcement Bar
**Role:** Top-of-page notice for product news or company updates

Fire-to-Red gradient background (linear 90deg, #bc0400 → #fe0600), Pure White text at 14px Plain weight 300, full-bleed. Contains a white ghost 'Learn More' button and a dismiss × icon at right.

### Hero Headline
**Role:** Primary page-level title - the largest typographic statement on each page

Plain Ultrathin weight 100, Pure White (#ffffff), 56–83px size range with -0.02em letter-spacing. 1.0–1.1 line-height. Sits left-aligned in the hero with a generous left margin, paired with a 3D generative ribbon or product mockup on the right.

### Dashboard / Product Screenshot
**Role:** In-context product visuals embedded in cards and sections

Contained within a 35px-radius card with a 1px crimson border (#2d1012). The screenshot itself uses a dark UI with Nava Red and Fire data accents. Rendered with a slight inset shadow or border to separate from the card background.

### Navigation Menu
**Role:** Primary top-right vertical navigation list

Plain weight 300 at 14–16px, Pure White text, no background. Vertically stacked right-aligned links with ~14px row gap. The 'Login' item is rendered as a 48px-radius ghost pill button with a 1px white border.

### Brand Logo Lockup
**Role:** Wordmark + glyph in the top-left header position

Custom crescent/glyph mark in Pure White followed by lowercase 'galileo' wordmark in Plain weight 300 at ~20px, white. Sits in the top-left of the header with 32px margin from the left edge.

## Do and Don'ts

### Do
- Use Plain Ultrathin weight 100 for all hero and section-level headlines at 42px or larger
- Use 48px border-radius for all buttons, nav pills, and floating action triggers
- Use 35px border-radius for all cards, panels, and content containers
- Use #fe0600 exclusively for primary filled actions and active states - never another color
- Use 0.25em letter-spacing (2.5px) on all 10px uppercase eyebrow labels
- Separate dark surfaces with 1px #2d1012 hairlines, not drop shadows
- Pair the fire-to-red gradient only with full-bleed banner surfaces, never inside cards

### Don't
- Never use weight 600 or 700 for headlines - the ultrathin register is the signature
- Never add drop shadows to cards or buttons - the system is flat by design
- Never use more than one vivid accent color per surface; red and fire should not compete on the same element
- Never use solid underlines on links - use the 1px Ash Rose (#d4a5a5) bottom border instead
- Never set body copy below weight 300 - the whole system is thin, but body must remain readable
- Never use sharp corners (0px or 4px radius) on interactive elements - all buttons, inputs, and cards use generous radii
- Never introduce a second dark-canvas color outside #000000 and #14090a - surface depth comes from the two-step shift between them

## Surfaces

| Level | Name | Value | Purpose |
|-------|------|-------|---------|
| 0 | Void Canvas | `#000000` | Page-level background, the obsidian base layer |
| 1 | Obsidian Burgundy Card | `#14090a` | Card and panel surfaces sitting on the void canvas |
| 2 | Light Content Surface | `#ffffff` | Light-theme content cards, dashboard mockups, and section inversions |

## Elevation

Galileo does not use drop shadows for elevation. Depth is achieved through hairline crimson borders (#2d1012, #5e1f25), subtle surface color shifts between #000000 and #14090a, and generous border-radius. This flat-architectural approach keeps the dark canvas clean and lets the vivid red accent do the visual lifting.

## Imagery

The visual identity is anchored by a single hero motif: a large 3D-rendered sculpture of translucent fire-red glass links or liquid generative ribbons, occupying roughly 40% of the hero viewport on the right side. The sculpture has a glossy, refractive quality with deep red-to-fire gradient surfaces and no hard edges. Beyond the hero, the site uses minimal imagery - product dashboard screenshots rendered in a dark UI with Nava Red and Fire data accents, set inside rounded cards. No lifestyle photography, no people, no environmental shots. Icons are outlined with 1.5–2px strokes in ash rose or red. The overall impression is abstract, premium, and product-focused - the technology itself is the visual subject.

## Layout

Max-width 1200px centered container with a 32–64px outer gutter. The hero is a full-bleed dark band with a split layout: weight-100 headline left-aligned occupying 45% of width, 3D glass sculpture right-aligned at 40% with 40–80px of breathing room between text and image. Below the hero, sections alternate between full-bleed dark and contained light cards, separated by 64px vertical gaps. The logo-and-top-bar sits 24px from the top edge with right-aligned vertical nav. Content blocks within sections use a 2-column text-plus-visual split or a single centered headline stack. Logo strip below the hero is a single centered row of 5–6 partner logos on a dark band. Product feature sections use 2-column layouts with a tabbed pill nav at top, headline + CTA on the left, and a rounded dashboard card on the right. The floating 'Talk With Gala' chat trigger is fixed at bottom-center on all viewports.

## Agent Prompt Guide

**Quick Color Reference**
- text (primary): #ffffff
- text (secondary): #d4a5a5
- text (tertiary): #a86d70
- background (page): #000000
- background (card dark): #14090a
- background (card light): #ffffff
- border (hairline): #2d1012
- border (subtle): #5e1f25
- accent: #bc0400
- primary action: #fe0600 (filled action)

**Example Component Prompts**
1. Build a hero headline: Plain Ultrathin weight 100, 83px, #ffffff, line-height 1.0, letter-spacing -1.66px. Left-aligned, max-width 520px. Below it a Plain Light weight 300 description at 16px, #d4a5a5, line-height 1.8. Primary CTA: 48px-radius pill, #fe0600 fill, white text, 22px×14px padding.
2. Build a dark feature card: #14090a background, 1px #2d1012 border, 35px radius, 32px padding. Inside: an Ash Rose (#d4a5a5) eyebrow label at 10px with 2.5px letter-spacing, then a Plain Ultralight weight 100 heading at 28px in white with -0.56px tracking.
3. Build a light content card: #ffffff background, 1px #5e1f25 border, 35px radius, 32px padding. Dark text (#14090a) body copy at 16px Plain Light weight 300. Embed a dashboard screenshot with a Nava Red accent header bar.
4. Build the announcement bar: full-bleed linear gradient from #bc0400 to #fe0600, 14px white Plain weight 300 text, a ghost 'Learn More' button (1px white border, 48px radius, 22px×14px padding) and a dismiss × at right.
5. Build a product tab nav: horizontal row of pill tabs, active tab has #fe0600 fill with white 14px text, inactive tabs are transparent with a faint #5e1f25 border. Tabs have 17px radius and 22px×14px padding. 9px gap between tabs.

## Gradient System

Two gradients are signature: a Fire-to-Red horizontal sweep (linear 90deg, #bc0400 → #fe0600) used for the announcement bar and any full-bleed brand banners, and a dark-maroon-to-fire micro-gradient (#5e1f25 → #bc0400) used for smaller UI accents. Gradients always flow left-to-right and always involve the Nava Red (#fe0600) as the terminal color - never the starting point. This creates a consistent sense of energy moving into the brand color.

## Typographic Voice

Plain is a custom geometric face used in an unusually thin register. Weight 100 at 42–147px is the brand most aggressive differentiator: most fintech sites use weight 600–700 for headlines to project authority. Galileo ultrathin weight projects authority through restraint - the type almost dissolves, which forces the surrounding negative space and the red accent to carry the visual weight. The 0.25em tracked-out 10px eyebrow label is the counterpoint: tightly tracked large display paired with wide-tracked tiny caps creates a dramatic scale contrast. Body copy sits at weight 300 (Light) at 16px, one weight step lighter than typical - the whole system leans thin.

## Similar Brands

- **Mercury** - Same dark-canvas fintech premium aesthetic with a single vivid accent color (Mercury uses violet) and thin geometric headlines
- **Ramp** - Dark-mode financial platform with a single electric accent and ultralight display type floating on a near-black canvas
- **Modern Treasury** - Deep dark theme with vivid primary actions and the same hairline-border card separation approach
- **Plaid** - Developer-facing fintech with dark UI, monochromatic palette, and abstract 3D illustration as the hero motif
- **Linear** - Thin-weight display type, generous border-radius, and a single vivid accent color punching through a dark, quiet canvas

## Quick Start

### CSS Custom Properties

```css
:root {
  /* Colors */
  --color-nava-black: #000000;
  --color-obsidian-burgundy: #14090a;
  --color-inkline-crimson: #2d1012;
  --color-ash-rose: #d4a5a5;
  --color-muted-coral: #a86d70;
  --color-dusk-maroon: #5e1f25;
  --color-nava-white: #fefefe;
  --color-pure-white: #ffffff;
  --color-nava-red: #fe0600;
  --color-nava-fire: #bc0400;
  --color-ember-glow: #e62800;
  --color-gradient-fire-red: #bc0400;
  --gradient-gradient-fire-red: linear-gradient(90deg, rgb(188, 4, 0) 0%, rgb(254, 6, 0) 100%);

  /* Typography - Font Families */
  --font-times: 'Times', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-plain: 'Plain', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-plain-light: 'Plain Light', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-plain-ultralight: 'Plain Ultralight', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-plain-ultrathin: 'Plain Ultrathin', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography - Scale */
  --text-eyebrow: 10px;
  --leading-eyebrow: 1.2;
  --tracking-eyebrow: 2.5px;
  --text-caption: 12px;
  --leading-caption: 1.5;
  --text-body: 16px;
  --leading-body: 1.3;
  --text-subheading: 28px;
  --leading-subheading: 1.3;
  --tracking-subheading: -0.56px;
  --text-heading-sm: 42px;
  --leading-heading-sm: 1.1;
  --tracking-heading-sm: -0.84px;
  --text-heading: 56px;
  --leading-heading: 1.1;
  --tracking-heading: -1.12px;
  --text-heading-lg: 83px;
  --leading-heading-lg: 1;
  --tracking-heading-lg: -1.66px;
  --text-display: 147px;
  --leading-display: 0.8;
  --tracking-display: -2.94px;

  /* Typography - Weights */
  --font-weight-thin: 100;
  --font-weight-light: 300;
  --font-weight-regular: 400;

  /* Spacing */
  --spacing-unit: 4px;
  --spacing-4: 4px;
  --spacing-16: 16px;
  --spacing-20: 20px;
  --spacing-52: 52px;
  --spacing-64: 64px;
  --spacing-104: 104px;
  --spacing-196: 196px;

  /* Layout */
  --page-max-width: 1200px;
  --section-gap: 64px;
  --card-padding: 32px;
  --element-gap: 9px;

  /* Border Radius */
  --radius-sm: 0.864px;
  --radius-2xl: 17.352px;
  --radius-3xl: 34.704px;
  --radius-full: 47.7072px;
  --radius-full-2: 360px;

  /* Named Radii */
  --radius-tags: 17px;
  --radius-cards: 35px;
  --radius-inputs: 35px;
  --radius-buttons: 48px;

  /* Surfaces */
  --surface-void-canvas: #000000;
  --surface-deep-indigo-card: #14090a;
  --surface-light-content-surface: #ffffff;
}
```

### Tailwind v4

```css
@theme {
  /* Colors */
  --color-nava-black: #000000;
  --color-obsidian-burgundy: #14090a;
  --color-inkline-crimson: #2d1012;
  --color-ash-rose: #d4a5a5;
  --color-muted-coral: #a86d70;
  --color-dusk-maroon: #5e1f25;
  --color-nava-white: #fefefe;
  --color-pure-white: #ffffff;
  --color-nava-red: #fe0600;
  --color-nava-fire: #bc0400;
  --color-ember-glow: #e62800;
  --color-gradient-fire-red: #bc0400;

  /* Typography */
  --font-times: 'Times', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-plain: 'Plain', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-plain-light: 'Plain Light', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-plain-ultralight: 'Plain Ultralight', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-plain-ultrathin: 'Plain Ultrathin', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography - Scale */
  --text-eyebrow: 10px;
  --leading-eyebrow: 1.2;
  --tracking-eyebrow: 2.5px;
  --text-caption: 12px;
  --leading-caption: 1.5;
  --text-body: 16px;
  --leading-body: 1.3;
  --text-subheading: 28px;
  --leading-subheading: 1.3;
  --tracking-subheading: -0.56px;
  --text-heading-sm: 42px;
  --leading-heading-sm: 1.1;
  --tracking-heading-sm: -0.84px;
  --text-heading: 56px;
  --leading-heading: 1.1;
  --tracking-heading: -1.12px;
  --text-heading-lg: 83px;
  --leading-heading-lg: 1;
  --tracking-heading-lg: -1.66px;
  --text-display: 147px;
  --leading-display: 0.8;
  --tracking-display: -2.94px;

  /* Spacing */
  --spacing-4: 4px;
  --spacing-16: 16px;
  --spacing-20: 20px;
  --spacing-52: 52px;
  --spacing-64: 64px;
  --spacing-104: 104px;
  --spacing-196: 196px;

  /* Border Radius */
  --radius-sm: 0.864px;
  --radius-2xl: 17.352px;
  --radius-3xl: 34.704px;
  --radius-full: 47.7072px;
  --radius-full-2: 360px;
}
```
