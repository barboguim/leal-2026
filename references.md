#reference 1
# Ui — Style Reference
> clinical blueprint on frosted paper

**Theme:** light

shadcn/ui is a monochromatic design-system workshop: pure white canvas, soft warm-gray surfaces, and large-radius cards floating on hairline borders. The interface is almost entirely achromatic — black text, white surfaces, gray secondary tones — with a single destructive red reserved for error states and nothing else. Typography leans on Geist's geometric neutrality with tight letter-spacing on display sizes, creating a quiet, code-adjacent feel that reads as developer infrastructure rather than consumer product.

## Tokens — Colors

| Name | Value | Token | Role |
|------|-------|-------|------|
| Canvas | `#f5f5f5` | `--color-canvas` | Page background, muted surface fills, secondary buttons |
| Paper | `#ffffff` | `--color-paper` | Card surfaces, popover backgrounds, primary button fills |
| Surface Alt | `#fafafa` | `--color-surface-alt` | Sidebar background, subtle card variant, input resting state |
| Ink | `#0a0a0a` | `--color-ink` | Primary text, headings, button labels, icon strokes |
| Ink Soft | `#171717` | `--color-ink-soft` | Filled button backgrounds, secondary text on light surfaces |
| Mid Gray | `#737373` | `--color-mid-gray` | Muted body text, placeholder text, helper labels, icon fills at rest |
| Hairline | `#e5e5e5` | `--color-hairline` | Borders, input outlines, card edges, badge outlines |
| Ember | `#e7000b` | `--color-ember` | Red decorative accent for icons, marks, and small graphic details. Use as a supporting accent, not as a status color |

## Tokens — Typography

### Geist — All interface text — body at 14px/400, headings ranging 24–48px/600, buttons at 13–14px/500. Geist's geometric letterforms and uniform stroke width create a developer-tool neutrality; weight 600 at 48px with -0.05em tracking produces tight, confident display headlines that feel engineered rather than editorial. · `--font-geist`
- **Substitute:** Inter
- **Weights:** 400, 500, 600
- **Sizes:** 12, 13, 14, 16, 18, 24, 30, 36, 48
- **Line height:** 1.10, 1.11, 1.20, 1.33, 1.43, 1.50, 1.56, 1.63, 2.00
- **Letter spacing:** -0.0500em at display (48px), -0.0250em at subheading (24–30px), 0.0500em at caption (12px uppercase). Tracking tightens aggressively at large sizes and loosens slightly at small uppercase labels.
- **OpenType features:** `"ss01" on, "cv11" on`
- **Role:** All interface text — body at 14px/400, headings ranging 24–48px/600, buttons at 13–14px/500. Geist's geometric letterforms and uniform stroke width create a developer-tool neutrality; weight 600 at 48px with -0.05em tracking produces tight, confident display headlines that feel engineered rather than editorial.

### Type Scale

| Role | Size | Line Height | Letter Spacing | Token |
|------|------|-------------|----------------|-------|
| caption | 12px | 1.33 | 0.6px | `--text-caption` |
| body | 14px | 1.43 | — | `--text-body` |
| body-lg | 16px | 1.5 | — | `--text-body-lg` |
| subheading | 18px | 1.56 | — | `--text-subheading` |
| heading-sm | 24px | 1.33 | -0.6px | `--text-heading-sm` |
| heading | 30px | 1.2 | -0.75px | `--text-heading` |
| heading-lg | 36px | 1.11 | -0.9px | `--text-heading-lg` |
| display | 48px | 1.1 | -2.4px | `--text-display` |

## Tokens — Spacing & Shapes

**Base unit:** 4px

**Density:** compact

### Spacing Scale

| Name | Value | Token |
|------|-------|-------|
| 4 | 4px | `--spacing-4` |
| 8 | 8px | `--spacing-8` |
| 12 | 12px | `--spacing-12` |
| 16 | 16px | `--spacing-16` |
| 20 | 20px | `--spacing-20` |
| 24 | 24px | `--spacing-24` |
| 48 | 48px | `--spacing-48` |

### Border Radius

| Element | Value |
|---------|-------|
| cards | 24px |
| small | 6px |
| badges | 18px |
| inputs | 18px |
| nested | 10px |
| buttons | 18px |

### Shadows

| Name | Value | Token |
|------|-------|-------|
| subtle | `oklab(0.145 -0.00000143796 0.00000340492 / 0.05) 0px 0px ...` | `--shadow-subtle` |
| subtle-2 | `lab(2.75381 0 0) 0px 0px 0px 0px` | `--shadow-subtle-2` |

### Layout

- **Page max-width:** 1280px
- **Section gap:** 48-80px
- **Card padding:** 20px
- **Element gap:** 8px

## Components

### Primary Filled Button
**Role:** High-emphasis action (Submit, Save, Create)

Background #0a0a0a, text #fafafa, border none, radius 18px, padding 0px 12px (compact) or 8px 16px (comfortable), font 14px Geist weight 500. Height ≈ 36–40px. The dark-on-light inversion is the only chromatic interaction in the system; the fully rounded radius (18px on a ~36px height) produces perfect pill geometry.

### Secondary Ghost Button
**Role:** Low-emphasis action (Cancel, Back)

Background #f5f5f5, text #0a0a0a, no border, radius 18px, padding 0px 12px or 8px 16px, font 14px weight 500. Soft gray fill reads as a tonal sibling to the primary rather than a muted alternative — both buttons share shape and type, differing only in lightness.

### Outline Button
**Role:** Tertiary action with visible boundary

Background transparent, text #0a0a0a, border 1px solid #e5e5e5, radius 18px, padding 0px 12px or 8px 10px. The hairline border defines the shape without weight — preferred when the button sits inside a card or alongside filled controls.

### Card
**Role:** Content container for blocks, previews, dashboard panels

Background #ffffff, radius 24px, border 1px solid #e5e5e5, shadow oklab(0.145/.05) 0 0 0 1px + rgba(0,0,0,0.1) 0 1px 3px + rgba(0,0,0,0.1) 0 1px 2px -1px, padding 20px. The 1px hairline shadow stacks with a faint elevation layer — cards sit visually raised but remain flat and understated.

### Nested Card Header/Footer
**Role:** Header or footer strip inside a card

Asymmetric radius — top corners 24px on header, bottom corners 24px on footer. Padding 20px horizontal, transparent fill. Provides a subtle tonal band within card boundaries without introducing a new color.

### Input Field
**Role:** Text entry, search, form controls

Background #f5f5f5 (resting) or transparent (inline), text #0a0a0a, border none at rest with 1px #e5e5e5 on focus, radius 18px, padding 8px 10px, font 14px weight 400. The soft gray fill differentiates the input from the card surface beneath it; focus replaces the fill with a 1px ring.

### Badge — Solid
**Role:** Tag, status pill, counter

Background #171717, text #fafafa, radius 18px, padding 2px 8px, font 12px weight 500. Pill-shaped at 18px radius — the minimum height creates a capsule tag.

### Badge — Soft
**Role:** Neutral label, category tag

Background #f5f5f5, text #171717, radius 18px, padding 2px 8px, font 12px weight 500. Same capsule geometry as solid badge, tonal variant.

### Badge — Outline
**Role:** Subtle tag with no fill

Transparent background, text #0a0a0a, radius 18px, padding 2px 8px. The lightest-weight tag — used when the label is informational rather than categorical.

### Sidebar Surface
**Role:** Left navigation panel

Background #fafafa, full-height, contained width. Sits one tonal step off the canvas (#f5f5f5) so the navigation reads as a distinct layer without introducing a divider line.

### Breadcrumb Trail
**Role:** Hierarchical path indicator

Inline text with chevron separators, font 14px weight 400, color #737373 for separators and #0a0a0a for the current segment. No background, no borders — purely typographic hierarchy.

### Stat Block
**Role:** Large numeric metric display

Label in 12–14px uppercase #737373, value in 30–48px weight 600 #0a0a0a with tight tracking. Progress bar or comparison text in 14px #737373. The block relies on typographic scale alone — no card chrome — to establish the metric.

### Search Trigger
**Role:** Command palette / search input

Background #f5f5f5, text #737373, radius 18px, padding 8px 10px, with a keyboard shortcut indicator (e.g., ⌘K) right-aligned. Functions as both a button and an input affordance.

### Destructive Action
**Role:** Delete, remove, revoke — error-adjacent interactions

Text or icon in #e7000b against the monochromatic palette. The red is the only chromatic hue in the system and appears exclusively in destructive or error contexts — it never decorates.

## Do's and Don'ts

### Do
- Use #0a0a0a on #ffffff for filled buttons — the dark inversion is the only primary action treatment.
- Maintain 18px radius on all buttons, inputs, and badges for perfect pill geometry; use 24px radius only on cards.
- Set display headlines at 48px/600 with -0.0500em tracking — Geist's geometric weight at this size with aggressive tightening produces the engineered headline voice.
- Reserve #e7000b exclusively for destructive states; never use it for decoration, branding, or non-error emphasis.
- Stack card shadows as 1px hairline + 1px + 2px offset — the combined effect is a barely-perceptible elevation that reads as 'card' without drama.
- Use #f5f5f5 for secondary surfaces and inputs; use #fafafa for sidebar and subtle card variants — the three-tone surface stack (canvas → soft → paper) creates layering without borders.

### Don't
- Do not introduce chromatic brand colors beyond #e7000b — the monochromatic palette is the system.
- Do not use border-radius values other than 18px (interactive) or 24px (containers); avoid square corners on any element.
- Do not skip the 1px hairline border on cards — the shadow alone does not define the card edge in this system.
- Do not set body text below 14px or above #737373 lightness — the type scale is deliberately compact.
- Do not apply gradients, colored shadows, or accent fills — every surface is a solid tone.
- Do not use letter-spacing wider than 0.05em or tighter than -0.05em; tracking outside this range breaks the typographic system.
- Do not mix filled and outline buttons of the same size in a single row without visual rhythm — alternate ghost or secondary variants.

## Surfaces

| Level | Name | Value | Purpose |
|-------|------|-------|---------|
| 0 | Canvas | `#f5f5f5` | Page background, broadest layer |
| 1 | Sidebar | `#fafafa` | Navigation surface, one step lighter than canvas |
| 2 | Card | `#ffffff` | Primary content container, brightest surface |
| 3 | Input Fill | `#f5f5f5` | Resting input field, matches canvas tone for subtle differentiation |

## Elevation

- **Card:** `0 0 0 1px rgba(23,23,23,0.05), 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)`
- **Button (filled):** `none — relies on tonal contrast, not shadow`
- **Input (focus):** `1px solid #e5e5e5 ring, no offset shadow`

## Imagery

Minimal imagery — the system is almost entirely UI. No hero photography, no illustrations, no decorative graphics. Product showcases are rendered as component mockups (cards, inputs, buttons) in a grid, serving as both documentation and visual content. Icons are thin-stroke geometric marks (likely Lucide-derived) at 1.5–2px stroke weight in #0a0a0a or #737373, used sparingly as functional cues. The visual language IS the UI components themselves — the page functions as a living style guide where every visible element is a design token made visible.

## Agent Prompt Guide

**Quick Color Reference**
- Canvas/background: #f5f5f5
- Card/surface: #ffffff
- Primary text: #0a0a0a
- Muted text: #737373
- Border: #e5e5e5
- primary action: #171717 (filled action)
- Destructive: #e7000b

**Example Component Prompts**
1. Create a dashboard stat card: white (#ffffff) background, 24px radius, 1px solid #e5e5e5 border, shadow 0 0 0 1px rgba(23,23,23,0.05) + 0 1px 3px rgba(0,0,0,0.1) + 0 1px 2px -1px rgba(0,0,0,0.1), 20px padding. Label in 12px uppercase #737373, value in 36px Geist weight 600 #0a0a0a with -0.025em tracking.

2. Create a filled dark button: background #0a0a0a, text #fafafa, no border, 18px radius, padding 0px 12px, font 14px Geist weight 500. Height 36px. No shadow — tonal contrast only.

3. Create a ghost secondary button: background #f5f5f5, text #0a0a0a, no border, 18px radius, padding 0px 12px, font 14px weight 500. Same dimensions as the filled button for visual parity.

4. Create an input field: background #f5f5f5, text #0a0a0a, placeholder #737373, no border at rest, 18px radius, padding 8px 10px, font 14px weight 400. On focus: 1px solid #e5e5e5 ring with no offset.

5. Create a badge tag: background #171717, text #fafafa, 18px radius (full pill), padding 2px 8px, font 12px Geist weight 500.

## Design Philosophy

shadcn/ui is built on three principles visible in every token: (1) achromatic by default — color is absence, not expression; (2) radius defines hierarchy — 18px for interactive elements, 24px for containers, never anything in between; (3) elevation is whisper-quiet — the card shadow is barely perceptible, relying on 1px hairlines and tonal contrast rather than dramatic drop shadows. The system is designed to be copied, modified, and owned — every value is explicit, every token is simple, and nothing is locked behind abstraction.

## Similar Brands

- **Vercel** — Same monochromatic palette, same Geist/geometric sans pairing, same pill-shaped buttons with tight letter-spacing on display text
- **Linear** — Identical approach to monochromatic UI with single accent for destructive states, tight typographic tracking, and hairline-bordered cards
- **Radix UI** — Same developer-tool visual language — neutral surfaces, geometric type, and component-first documentation layout
- **Tailwind UI** — Matching restrained palette, identical border-radius scale (large radii on containers), and code-adjacent minimal chrome
- **Cal.com** — Same compact density, same pill-badge system, and the same achromatic-first approach with red reserved for errors

## Quick Start

### CSS Custom Properties

```css
:root {
  /* Colors */
  --color-canvas: #f5f5f5;
  --color-paper: #ffffff;
  --color-surface-alt: #fafafa;
  --color-ink: #0a0a0a;
  --color-ink-soft: #171717;
  --color-mid-gray: #737373;
  --color-hairline: #e5e5e5;
  --color-ember: #e7000b;

  /* Typography — Font Families */
  --font-geist: 'Geist', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 12px;
  --leading-caption: 1.33;
  --tracking-caption: 0.6px;
  --text-body: 14px;
  --leading-body: 1.43;
  --text-body-lg: 16px;
  --leading-body-lg: 1.5;
  --text-subheading: 18px;
  --leading-subheading: 1.56;
  --text-heading-sm: 24px;
  --leading-heading-sm: 1.33;
  --tracking-heading-sm: -0.6px;
  --text-heading: 30px;
  --leading-heading: 1.2;
  --tracking-heading: -0.75px;
  --text-heading-lg: 36px;
  --leading-heading-lg: 1.11;
  --tracking-heading-lg: -0.9px;
  --text-display: 48px;
  --leading-display: 1.1;
  --tracking-display: -2.4px;

  /* Typography — Weights */
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;

  /* Spacing */
  --spacing-unit: 4px;
  --spacing-4: 4px;
  --spacing-8: 8px;
  --spacing-12: 12px;
  --spacing-16: 16px;
  --spacing-20: 20px;
  --spacing-24: 24px;
  --spacing-48: 48px;

  /* Layout */
  --page-max-width: 1280px;
  --section-gap: 48-80px;
  --card-padding: 20px;
  --element-gap: 8px;

  /* Border Radius */
  --radius-md: 6px;
  --radius-lg: 10px;
  --radius-xl: 14px;
  --radius-2xl: 18px;
  --radius-3xl: 24px;

  /* Named Radii */
  --radius-cards: 24px;
  --radius-small: 6px;
  --radius-badges: 18px;
  --radius-inputs: 18px;
  --radius-nested: 10px;
  --radius-buttons: 18px;

  /* Shadows */
  --shadow-subtle: oklab(0.145 -0.00000143796 0.00000340492 / 0.05) 0px 0px 0px 1px, rgba(0, 0, 0, 0.1) 0px 1px 3px 0px, rgba(0, 0, 0, 0.1) 0px 1px 2px -1px;
  --shadow-subtle-2: lab(2.75381 0 0) 0px 0px 0px 0px;

  /* Surfaces */
  --surface-canvas: #f5f5f5;
  --surface-sidebar: #fafafa;
  --surface-card: #ffffff;
  --surface-input-fill: #f5f5f5;
}
```

### Tailwind v4

```css
@theme {
  /* Colors */
  --color-canvas: #f5f5f5;
  --color-paper: #ffffff;
  --color-surface-alt: #fafafa;
  --color-ink: #0a0a0a;
  --color-ink-soft: #171717;
  --color-mid-gray: #737373;
  --color-hairline: #e5e5e5;
  --color-ember: #e7000b;

  /* Typography */
  --font-geist: 'Geist', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 12px;
  --leading-caption: 1.33;
  --tracking-caption: 0.6px;
  --text-body: 14px;
  --leading-body: 1.43;
  --text-body-lg: 16px;
  --leading-body-lg: 1.5;
  --text-subheading: 18px;
  --leading-subheading: 1.56;
  --text-heading-sm: 24px;
  --leading-heading-sm: 1.33;
  --tracking-heading-sm: -0.6px;
  --text-heading: 30px;
  --leading-heading: 1.2;
  --tracking-heading: -0.75px;
  --text-heading-lg: 36px;
  --leading-heading-lg: 1.11;
  --tracking-heading-lg: -0.9px;
  --text-display: 48px;
  --leading-display: 1.1;
  --tracking-display: -2.4px;

  /* Spacing */
  --spacing-4: 4px;
  --spacing-8: 8px;
  --spacing-12: 12px;
  --spacing-16: 16px;
  --spacing-20: 20px;
  --spacing-24: 24px;
  --spacing-48: 48px;

  /* Border Radius */
  --radius-md: 6px;
  --radius-lg: 10px;
  --radius-xl: 14px;
  --radius-2xl: 18px;
  --radius-3xl: 24px;

  /* Shadows */
  --shadow-subtle: oklab(0.145 -0.00000143796 0.00000340492 / 0.05) 0px 0px 0px 1px, rgba(0, 0, 0, 0.1) 0px 1px 3px 0px, rgba(0, 0, 0, 0.1) 0px 1px 2px -1px;
  --shadow-subtle-2: lab(2.75381 0 0) 0px 0px 0px 0px;
}
```


#reference 2

# Felt — Style Reference
> topographic atlas at dusk — moss-green pages, serif headlines, one amber needle

**Theme:** dark

Felt renders as a cartographer's field journal at dusk: a deep mossy-green canvas carries oversized editorial serif headlines that feel pulled from a vintage atlas, while a grotesque sans handles utility text. The warm amber accent appears sparingly — a compass needle against the green — punctuating CTAs, links, and interactive borders without ever flooding the surface. Layout is centered, magazine-like, with generous breathing room and full-width product reveals that feel like fold-out map spreads. The visual rhythm alternates between typographic hero zones and embedded product UI, creating a sense of a working tool rather than a marketing site.

## Tokens — Colors

| Name | Value | Token | Role |
|------|-------|-------|------|
| Moss Canvas | `#314218` | `--color-moss-canvas` | Page background, hero sections, dominant canvas — the deep mossy green that carries the entire site and grounds the editorial atmosphere |
| Fern | `#3d521e` | `--color-fern` | Mid-green surface for cards, elevated panels, and the topside of the surface stack |
| Lichen | `#64754b` | `--color-lichen` | Muted green for secondary surfaces, borders on cards, and subtle dividers against the canvas |
| Forest Floor | `#212f0c` | `--color-forest-floor` | Deeper green for nested surface layers and inset product UI backgrounds |
| Deep Bog | `#18210c` | `--color-deep-bog` | Darkest green for the deepest surface layer, code blocks, and high-contrast panels |
| Amber Compass | `#dc8c46` | `--color-amber-compass` | Primary action — filled CTA buttons, link borders, active link text. The single warm accent that cuts through the green monochrome like a compass needle |
| Bone White | `#ffffff` | `--color-bone-white` | Primary text, heading color, button text on amber fills, and the dominant border for ghost/outlined controls |
| Parchment | `#eeeeee` | `--color-parchment` | Light surface for embedded product UI, inset map views, and light-mode panel surfaces against the dark canvas |
| Charcoal | `#333333` | `--color-charcoal` | Text and borders inside the light parchment product UI panels — the dark-on-light text color for embedded app surfaces |
| Limestone | `#d8dcd2` | `--color-limestone` | Soft warm-tinted gray for badge backgrounds, subtle borders, and muted helper text inside light panels |
| Ink | `#000000` | `--color-ink` | SVG fills, max-contrast elements, and the map marker pin color |

## Tokens — Typography

### Arial — Arial — detected in extracted data but not described by AI · `--font-arial`
- **Weights:** 400
- **Sizes:** 14px, 16px
- **Line height:** 1.25, 1.33, 1.43
- **Role:** Arial — detected in extracted data but not described by AI

### GT Alpina Standard — Display and heading serif — the editorial headline face. Used at large sizes for hero headlines and section titles. The tight negative tracking (-0.033em to -0.040em) and line-height under 1.0 give the serif a compressed, almost carved-into-stone quality that evokes old cartographic title plates. This is the signature type choice: a humanist serif that feels hand-drawn rather than mechanical. · `--font-gt-alpina-standard`
- **Substitute:** Fraunces, Tiempos Headline, Playfair Display
- **Weights:** 300, 400
- **Sizes:** 28px, 36px, 43px, 46px, 50px, 86px
- **Line height:** 0.80, 0.96, 1.00, 1.11, 1.33
- **Letter spacing:** -0.0400em at 86px, -0.0330em at 36-50px
- **Role:** Display and heading serif — the editorial headline face. Used at large sizes for hero headlines and section titles. The tight negative tracking (-0.033em to -0.040em) and line-height under 1.0 give the serif a compressed, almost carved-into-stone quality that evokes old cartographic title plates. This is the signature type choice: a humanist serif that feels hand-drawn rather than mechanical.

### Atlas Grotesk — Primary UI and body sans-serif — handles navigation, body text, button labels, badges, and links. The slight positive tracking (0.033em) on body sizes adds legibility on the dark green canvas. The grotesque geometry provides a clean utility counterpoint to the expressive serif headlines. · `--font-atlas-grotesk`
- **Substitute:** Inter, Söhne, Helvetica Neue
- **Weights:** 300, 400, 500, 700
- **Sizes:** 12px, 14px, 16px, 18px, 19px, 20px
- **Line height:** 1.00, 1.11, 1.20, 1.25, 1.30, 1.33, 1.43, 1.50, 1.56
- **Letter spacing:** 0.0330em
- **Role:** Primary UI and body sans-serif — handles navigation, body text, button labels, badges, and links. The slight positive tracking (0.033em) on body sizes adds legibility on the dark green canvas. The grotesque geometry provides a clean utility counterpoint to the expressive serif headlines.

### Times New Roman — Fallback system serif at extreme display sizes. The 101px / 0.88 line-height ratio confirms the compressed display treatment for the largest headlines. · `--font-times-new-roman`
- **Substitute:** system serif
- **Weights:** 400
- **Sizes:** 36px, 101px
- **Line height:** 0.88, 2.46
- **Role:** Fallback system serif at extreme display sizes. The 101px / 0.88 line-height ratio confirms the compressed display treatment for the largest headlines.

### Type Scale

| Role | Size | Line Height | Letter Spacing | Token |
|------|------|-------------|----------------|-------|
| caption | 12px | 1.43 | 0.4px | `--text-caption` |
| body-sm | 14px | 1.43 | 0.46px | `--text-body-sm` |
| body | 16px | 1.5 | 0.53px | `--text-body` |
| subheading | 19px | 1.33 | — | `--text-subheading` |
| heading-sm | 28px | 1.11 | -0.92px | `--text-heading-sm` |
| heading | 36px | 1 | -1.19px | `--text-heading` |
| heading-lg | 50px | 0.96 | -1.65px | `--text-heading-lg` |
| display | 86px | 0.88 | -3.44px | `--text-display` |

## Tokens — Spacing & Shapes

**Base unit:** 4px

**Density:** comfortable

### Spacing Scale

| Name | Value | Token |
|------|-------|-------|
| 4 | 4px | `--spacing-4` |
| 8 | 8px | `--spacing-8` |
| 12 | 12px | `--spacing-12` |
| 16 | 16px | `--spacing-16` |
| 20 | 20px | `--spacing-20` |
| 24 | 24px | `--spacing-24` |
| 32 | 32px | `--spacing-32` |
| 36 | 36px | `--spacing-36` |
| 48 | 48px | `--spacing-48` |
| 64 | 64px | `--spacing-64` |
| 72 | 72px | `--spacing-72` |
| 80 | 80px | `--spacing-80` |
| 120 | 120px | `--spacing-120` |
| 144 | 144px | `--spacing-144` |
| 160 | 160px | `--spacing-160` |

### Border Radius

| Element | Value |
|---------|-------|
| cards | 6px |
| badges | 6px |
| images | 6px |
| inputs | 6px |
| buttons | 20px |

### Shadows

| Name | Value | Token |
|------|-------|-------|
| sm | `rgba(0, 0, 0, 0.2) 0px 2px 5px 0px` | `--shadow-sm` |

### Layout

- **Page max-width:** 1200px
- **Section gap:** 80px
- **Card padding:** 24px
- **Element gap:** 12px

## Components

### Amber CTA Button
**Role:** Primary action — filled button for conversion moments

Filled #dc8c46 background, white (#ffffff) text in Atlas Grotesk 16px weight 500, tracking 0.033em. 20px border-radius (pilled). Horizontal padding 20-24px, vertical padding 12-16px. No border. Includes a white play-arrow icon inline at the right.

### Ghost Link Button
**Role:** Secondary action — text link with underline border treatment

No fill, no border. Atlas Grotesk 16px weight 400, #ffffff text. Underline created by a 1px white bottom border. Used for "Book a demo" style secondary CTAs.

### Navigation Bar
**Role:** Top-level site navigation

Transparent on Moss Canvas. Felt wordmark in white serif at left. Nav items (PLATFORM, INDUSTRIES, RESOURCES, PRICING) in Atlas Grotesk 12px weight 500, uppercase, 0.033em tracking, white. Right side: "BOOK A DEMO" and "LOG IN" as ghost text links, "SIGN UP" as a filled Amber CTA with play icon.

### Hero Section
**Role:** Above-the-fold headline and CTA zone

Centered layout on Moss Canvas. Headline in GT Alpina Standard 86px weight 300, white, line-height 0.88, letter-spacing -3.44px. Subtitle in Atlas Grotesk 18px weight 400, #eeeeee. Two CTAs side by side: Amber CTA + Ghost Link.

### Scrolling Ticker Banner
**Role:** Top announcement bar

Full-width strip. White text on Moss Canvas (#314218). Atlas Grotesk 12px weight 500, uppercase, repeated headline text with separators. Sits above the navigation.

### Product UI Panel
**Role:** Embedded application screenshot / product surface

Light surface (#ffffff or #eeeeee) with rounded corners 6px. Dark text (#333333) inside. Subtle shadow rgba(0,0,0,0.2) 0px 2px 5px. Contains toolbars, map canvases, and library sidebars — mimics the actual Felt product.

### Client Logo Row
**Role:** Social proof — trusted-by brand logos

Horizontal row of client logos (Lyft, Lime, Turo, Cushman & Wakefield) rendered in white on Moss Canvas. Section title "Leading a modern GIS movement" in GT Alpina Standard 36px weight 300, white, centered above.

### Feature Section
**Role:** Mid-page content blocks with headline + product visual

Centered serif headline (GT Alpina Standard 36-50px, white) followed by Atlas Grotesk 18px subtext, then a full-width Product UI Panel below. Generous 80px vertical gap between sections.

### Badge / Tag
**Role:** Category labels and metadata tags

Limestone (#d8dcd2) background, small radius 6px, Atlas Grotesk 12px weight 500, 0.033em tracking. Minimal padding 2px 6px.

### Map Marker Pin
**Role:** Interactive map point indicator

#dc8c46 (Amber) circular pin with a white border, placed on the map canvas. Small drop shadow. Acts as the brand's visual signature on the product surface.

## Do's and Don'ts

### Do
- Use GT Alpina Standard weight 300 for all display and section headlines — the thin serif is the brand's most distinctive choice and must carry the editorial voice
- Set display headlines at 86px with line-height 0.88 and letter-spacing -3.44px for the compressed, carved-into-stone effect
- Use Amber Compass (#dc8c46) exclusively for filled CTAs and accent moments — never as a surface fill or decorative wash
- Step surfaces using the green scale: Moss Canvas (#314218) → Fern (#3d521e) → Lichen (#64754b) for elevation, not shadows
- Set body and UI text in Atlas Grotesk weight 400 with 0.033em letter-spacing for legibility on the dark green canvas
- Embed product UI panels in light surface (#ffffff) with 6px radius and the single subtle shadow to create contrast against the dark page
- Maintain centered, magazine-style layouts with 80px section gaps — the page rhythm should feel like turning pages in an atlas

### Don't
- Don't use Amber Compass (#dc8c46) for body text, backgrounds, or large surface areas — it loses its compass-needle effect when overused
- Don't set serif headlines at line-height above 1.0 — the compressed treatment is essential to the editorial feel
- Don't apply multiple shadow layers — Felt uses elevation through color stepping, not shadow stacks
- Don't use pure black (#000000) as a page background — the mossy green tones are the canvas, not black
- Don't replace GT Alpina Standard with a geometric or grotesque display face — the serif is the brand identity
- Don't use border-radius above 6px on cards, images, or product panels — only buttons get the 20px pill radius
- Don't introduce new accent hues — the entire palette is green monochrome plus one warm amber; any other color breaks the system

## Surfaces

| Level | Name | Value | Purpose |
|-------|------|-------|---------|
| 0 | Moss Canvas | `#314218` | Primary page background and hero zones |
| 1 | Fern | `#3d521` | First elevation — cards and content panels sitting on the canvas |
| 2 | Lichen | `#64754b` | Secondary surface for sub-cards and dividers |
| 3 | Bone White | `#ffffff` | Inverted product UI surfaces (embedded map app panels) |

## Elevation

- **Embedded product UI panels:** `rgba(0, 0, 0, 0.2) 0px 2px 5px 0px`

## Imagery

Imagery is dominated by embedded product screenshots showing the Felt map application — these are full-width, light-surface panels with real GIS map content (street maps, satellite views, data overlays, map markers). The product UI itself IS the hero imagery. No lifestyle photography, no stock imagery, no decorative illustration. The only non-product visual elements are topographic contour-line patterns in muted green (#64754b) that appear as background decoration on hero sections, evoking actual cartographic map texture. Client logos appear in white monochrome. The map marker pin (#dc8c46 with white border) serves as the brand's recurring visual signature across product surfaces.

## Layout

Centered, magazine-style page layout with max-width 1200px for content. Hero is full-bleed dark green with centered oversized serif headline, subtitle, and two side-by-side CTAs. Below the hero, a full-width embedded product UI panel breaks the layout to a wider reveal (like a fold-out map spread). Sections alternate between typographic hero zones (centered text, 80px vertical padding) and product reveal zones (full-width embedded app surfaces). A scrolling ticker banner sits at the very top. Navigation is a clean transparent bar overlaying the dark canvas. The page rhythm is: ticker → nav → hero headline → product reveal → social proof logos → feature section (headline + product) → repeating feature sections. All content is centered; no asymmetric or left-aligned compositions.

## Agent Prompt Guide

## Quick Color Reference
- Background (canvas): #314218 (Moss Canvas)
- Text: #ffffff (headings) / #eeeeee (body on dark)
- Border / divider: #64754b (Lichen) or #3d521e (Fern)
- Accent / brand: #dc8c46 (Amber Compass)
- Product surface: #ffffff (Bone White)
- primary action: #ffffff (filled action)

## Example Component Prompts

1. Create a Primary Action Button: #ffffff background, #eeeeee text, 9999px radius, compact pill padding. Use this filled treatment for the main CTA.

2. **Feature Section**: Moss Canvas background, centered content. Section headline: GT Alpina Standard 50px, weight 300, #ffffff, line-height 0.96, letter-spacing -1.65px, centered. Body text: Atlas Grotesk 18px, weight 400, #eeeeee, centered, max-width 720px. Below: full-width Product UI Panel — #ffffff surface, 6px border-radius, shadow rgba(0,0,0,0.2) 0px 2px 5px, containing a mock map interface with #333333 toolbar elements.

3. **Client Logo Row**: Moss Canvas background. Section title: GT Alpina Standard 36px, weight 300, #ffffff, centered. Below: horizontal row of 4–5 client logos in white monochrome, evenly spaced with 48px gaps, centered in the layout.

4. **Embedded Product Panel**: White (#ffffff) surface, 6px border-radius, shadow rgba(0,0,0,0.2) 0px 2px 5px 0px. Interior toolbar in #333333, Atlas Grotesk 14px. Map canvas fills the body. Amber map marker pin (#dc8c46 circle, 2px white border) at a notable location.


## Type & Tone

The visual voice is editorial-cartographic: think National Geographic meets a modern SaaS landing page. Serif headlines do the heavy emotional lifting while the grotesque sans handles all functional text. The amber accent acts as a compass needle — singular, precise, never decorative. Topographic contour-line patterns appear as background texture on hero sections to reinforce the mapping identity without resorting to literal map imagery. The overall effect should feel like opening a beautifully typeset atlas: authoritative, warm, and slightly adventurous.

## Similar Brands

- **Mapbox** — Both use dark canvas backgrounds with a single warm accent color and center their hero on embedded map product UI rather than abstract imagery
- **Notion** — Same editorial approach with oversized serif headlines on dark backgrounds, though Notion uses black rather than green canvas
- **Linear** — Dark monochromatic UI with one distinctive accent color, centered layouts, and serif/serif-adjacent display type for a premium editorial feel
- **Roam Research** — Both use nature-inspired dark canvas palettes (Roam uses deep navy, Felt uses moss green) with serif headlines and a single warm accent for interactive elements
- **Stamen Design** — Cartographic design studio aesthetic — mossy greens, topographic texture, and serif typography rooted in atlas and map traditions

## Quick Start

### CSS Custom Properties

```css
:root {
  /* Colors */
  --color-moss-canvas: #314218;
  --color-fern: #3d521e;
  --color-lichen: #64754b;
  --color-forest-floor: #212f0c;
  --color-deep-bog: #18210c;
  --color-amber-compass: #dc8c46;
  --color-bone-white: #ffffff;
  --color-parchment: #eeeeee;
  --color-charcoal: #333333;
  --color-limestone: #d8dcd2;
  --color-ink: #000000;

  /* Typography — Font Families */
  --font-arial: 'Arial', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-gt-alpina-standard: 'GT Alpina Standard', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-atlas-grotesk: 'Atlas Grotesk', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-times-new-roman: 'Times New Roman', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 12px;
  --leading-caption: 1.43;
  --tracking-caption: 0.4px;
  --text-body-sm: 14px;
  --leading-body-sm: 1.43;
  --tracking-body-sm: 0.46px;
  --text-body: 16px;
  --leading-body: 1.5;
  --tracking-body: 0.53px;
  --text-subheading: 19px;
  --leading-subheading: 1.33;
  --text-heading-sm: 28px;
  --leading-heading-sm: 1.11;
  --tracking-heading-sm: -0.92px;
  --text-heading: 36px;
  --leading-heading: 1;
  --tracking-heading: -1.19px;
  --text-heading-lg: 50px;
  --leading-heading-lg: 0.96;
  --tracking-heading-lg: -1.65px;
  --text-display: 86px;
  --leading-display: 0.88;
  --tracking-display: -3.44px;

  /* Typography — Weights */
  --font-weight-light: 300;
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-bold: 700;

  /* Spacing */
  --spacing-unit: 4px;
  --spacing-4: 4px;
  --spacing-8: 8px;
  --spacing-12: 12px;
  --spacing-16: 16px;
  --spacing-20: 20px;
  --spacing-24: 24px;
  --spacing-32: 32px;
  --spacing-36: 36px;
  --spacing-48: 48px;
  --spacing-64: 64px;
  --spacing-72: 72px;
  --spacing-80: 80px;
  --spacing-120: 120px;
  --spacing-144: 144px;
  --spacing-160: 160px;

  /* Layout */
  --page-max-width: 1200px;
  --section-gap: 80px;
  --card-padding: 24px;
  --element-gap: 12px;

  /* Border Radius */
  --radius-md: 6px;
  --radius-lg: 10px;
  --radius-2xl: 20px;

  /* Named Radii */
  --radius-cards: 6px;
  --radius-badges: 6px;
  --radius-images: 6px;
  --radius-inputs: 6px;
  --radius-buttons: 20px;

  /* Shadows */
  --shadow-sm: rgba(0, 0, 0, 0.2) 0px 2px 5px 0px;

  /* Surfaces */
  --surface-moss-canvas: #314218;
  --surface-fern: #3d521;
  --surface-lichen: #64754b;
  --surface-bone-white: #ffffff;
}
```

### Tailwind v4

```css
@theme {
  /* Colors */
  --color-moss-canvas: #314218;
  --color-fern: #3d521e;
  --color-lichen: #64754b;
  --color-forest-floor: #212f0c;
  --color-deep-bog: #18210c;
  --color-amber-compass: #dc8c46;
  --color-bone-white: #ffffff;
  --color-parchment: #eeeeee;
  --color-charcoal: #333333;
  --color-limestone: #d8dcd2;
  --color-ink: #000000;

  /* Typography */
  --font-arial: 'Arial', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-gt-alpina-standard: 'GT Alpina Standard', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-atlas-grotesk: 'Atlas Grotesk', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-times-new-roman: 'Times New Roman', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 12px;
  --leading-caption: 1.43;
  --tracking-caption: 0.4px;
  --text-body-sm: 14px;
  --leading-body-sm: 1.43;
  --tracking-body-sm: 0.46px;
  --text-body: 16px;
  --leading-body: 1.5;
  --tracking-body: 0.53px;
  --text-subheading: 19px;
  --leading-subheading: 1.33;
  --text-heading-sm: 28px;
  --leading-heading-sm: 1.11;
  --tracking-heading-sm: -0.92px;
  --text-heading: 36px;
  --leading-heading: 1;
  --tracking-heading: -1.19px;
  --text-heading-lg: 50px;
  --leading-heading-lg: 0.96;
  --tracking-heading-lg: -1.65px;
  --text-display: 86px;
  --leading-display: 0.88;
  --tracking-display: -3.44px;

  /* Spacing */
  --spacing-4: 4px;
  --spacing-8: 8px;
  --spacing-12: 12px;
  --spacing-16: 16px;
  --spacing-20: 20px;
  --spacing-24: 24px;
  --spacing-32: 32px;
  --spacing-36: 36px;
  --spacing-48: 48px;
  --spacing-64: 64px;
  --spacing-72: 72px;
  --spacing-80: 80px;
  --spacing-120: 120px;
  --spacing-144: 144px;
  --spacing-160: 160px;

  /* Border Radius */
  --radius-md: 6px;
  --radius-lg: 10px;
  --radius-2xl: 20px;

  /* Shadows */
  --shadow-sm: rgba(0, 0, 0, 0.2) 0px 2px 5px 0px;
}
```
