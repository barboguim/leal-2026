# references v2 — LEAL reconciled reference

> **Purpose of this file.** `references.md` (v1) contained two *complete, opinionated*
> design systems extracted wholesale: **shadcn/ui** (reference 1) and **Felt** (reference 2).
> Both are strong. But they contradict each other (light-monochrome-developer-tool vs.
> dark-moss-cartographic-editorial), and the previous `DESIGN.md` reconciled them by
> keeping only the *neutral intersection* of the two — which is exactly why the output
> kept coming out generic. This file records what we actually take from each, and why,
> so the decision is traceable and nobody re-litigates it blindly next pass.
>
> **The core decision (see DESIGN2.md §"What happened here" for the full narrative):**
> we commit to **Felt's editorial-cartographic point of view**, adapted to a *light*
> theme and *IBM Plex* type — NOT the timid middle. shadcn contributes structural
> discipline (surface-stepping logic, hairline restraint); Felt contributes the
> *personality* (a single warm accent, a serif display voice, atlas-instrument warmth,
> map-native confidence). We stop averaging them into blandness.

---

## Decision key

Each item below is tagged:

- **ADOPT** — taken into LEAL more or less as-is.
- **ADAPT** — taken, but changed to fit LEAL (light theme, IBM Plex, dense sidebar).
- **REJECT** — explicitly not used; recorded so it doesn't creep back in.

---

## Reference 1 — shadcn/ui (light, monochrome, developer-tool)

What it is: pure-white canvas, warm-gray surfaces, hairline borders, Geist type,
achromatic-plus-one-red. Engineered, quiet, code-adjacent.

| Item | Decision | Note |
|---|---|---|
| Light, neutral base theme | **ADOPT** | This is the theme LEAL already settled on and keeps. Correct for a map-first tool (light UI seams cleanly with light CartoDB Positron tiles). |
| Three-tone surface stack (canvas → soft → paper) creating layering **without borders** | **ADOPT** | This is the structural discipline worth keeping — depth via tonal stepping, not drop-shadow drama. LEAL's `--color-bg / --color-surface / --color-surface-muted` already mirror this. |
| Hairline-border restraint; barely-perceptible elevation | **ADOPT** | One quiet shadow, 1px borders. Keeps the "calm field instrument" feel. |
| Geist typeface | **REJECT** | LEAL uses IBM Plex Sans/Mono (settled — Plex Mono's tabular figures matter for vote columns; Geist has no equivalent advantage here). |
| Large radius scale (18px interactive / 24px containers, pill buttons) | **REJECT (adapt down)** | Too loose for a ~350px dense sidebar. LEAL uses compact 8/10px (see DESIGN2). shadcn's pill geometry reads as marketing-card, not instrument. |
| Achromatic-plus-one-red (`#e7000b` ember, destructive only) | **REJECT** | LEAL is *not* monochrome — it carries meaningful candidate/party/delta/demographic color. shadcn's "color is absence" philosophy is the opposite of what an electoral tool needs. |
| Stat block: label uppercase muted + large tabular value, no card chrome | **ADOPT** | Good pattern for LEAL's pinned Stats. Typographic hierarchy alone, no box. |

**Net from shadcn: structure and restraint, not identity.** Take the surface-stepping
logic and the hairline discipline. Leave the monochrome philosophy and the loose radius.

---

## Reference 2 — Felt (dark moss, cartographic, editorial)

What it is: moss-green canvas, GT Alpina thin serif at huge display sizes, Atlas Grotesk
for function, a single **amber compass** accent (`#dc8c46`), topographic contour texture,
elevation by color-stepping. "National Geographic meets modern SaaS. Authoritative, warm,
slightly adventurous."

| Item | Decision | Note |
|---|---|---|
| **Amber Compass accent `#dc8c46`** — single warm accent, "compass needle: singular, precise, never decorative" | **ADOPT** | **This is the most important single adoption.** It's the point of view LEAL was missing. Used for one accent role only (see DESIGN2 for exactly where). Never a surface fill, never decoration. |
| Editorial-cartographic *voice* (atlas-instrument, authoritative, warm) | **ADOPT (as direction)** | This is the felt-quality we want and DESIGN.md stripped. It's a compositional/tonal target, not a token. |
| Map-first framing / cartographic overlay discipline / map-as-hero | **ADOPT** | LEAL's floating-panel-over-map structure already has this bone structure — we lean into it rather than treating the map as a backdrop. |
| Serif *display* face for wordmark + section identity (Felt uses GT Alpina) | **ADAPT** | We do NOT license GT Alpina. We use a **free serif** (see DESIGN2 — a Google-hosted editorial serif) for the **LEAL wordmark and top-level section identity ONLY**, never body, never numbers. This is the single biggest visible change from the timid version. |
| Topographic contour-line background texture (muted, cartographic) | **ADAPT (optional, restrained)** | A very subtle contour/hairline motif is permissible *behind the panel header only*, at very low contrast, as a nod to the cartographic identity. Must not become decoration-for-its-own-sake or a "blob." Ship only if it reads as texture, not ornament. |
| Amber map-marker-pin-with-white-border as recurring brand signature | **ADAPT** | LEAL's markers are candidate-colored (data-bearing) so amber can't own them. But the amber accent can mark *the user's currently-selected / focused* local — a single "you are here / this is the active point" signature. |
| Moss-green dark canvas (`#314218` etc.) | **REJECT** | Contradicts the settled light theme. LEAL stays light. |
| GT Alpina at 86px, line-height 0.88, -3.44px tracking (carved-stone hero) | **REJECT** | That's a landing-page hero treatment. LEAL is an instrument, not a marketing page. The serif appears small, at wordmark/section scale, not hero scale. |
| Atlas Grotesk for functional text | **REJECT** | LEAL uses IBM Plex Sans for function. (Atlas is also not free.) |
| Elevation by color-stepping instead of shadow | **ADOPT** | Aligns with shadcn's surface-stack adoption above — consistent conclusion from both references: prefer tonal depth over shadow. |
| Centered magazine layout, 80px section gaps, fold-out reveals | **REJECT** | Landing-page rhythm. LEAL is a dense left-panel-over-map app; its spacing is compact (4px base), not editorial. |

**Net from Felt: the personality.** Take the amber accent, the serif *identity* voice, the
map-native warmth, the cartographic nod. Leave the dark canvas, the huge hero type, the
licensed fonts, the landing-page layout.

---

## The reconciled position (one paragraph)

LEAL is a **light**, dense, map-first electoral instrument that borrows shadcn's
**structural restraint** (tonal surface-stepping, hairline borders, quiet elevation, compact
radius) and Felt's **editorial-cartographic personality** (a single amber compass accent, a
free serif for the LEAL wordmark and section identity, map-as-hero framing, an optional very
subtle contour texture behind the header). Body and all functional/numeric text stays **IBM
Plex Sans / Mono**. The result should read like a *credible, warm, atlas-grade field
instrument* — not a monochrome developer console (too cold) and not a moss-green marketing
page (wrong medium), and specifically **not** the personality-free average of the two, which
is what the previous pass produced.

---

## What lives in code, not here

Exact LEAL base hexes (`--color-bg`, `--color-surface`, `--color-text`, candidate/party
colors, delta diverging scale, demographic indigo scale) live in
`app-web/src/lib/constants.js` and `index.css`'s `@theme` block. This file does not re-list
them — it would drift. The **only new token this reconciliation introduces** is the amber
accent and the serif display face; both are pinned in DESIGN2.md §Tokens, to be added to the
`@theme` block, not invented per-component.
