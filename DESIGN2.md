# LEAL Design Contract v2 — FINAL

> **Single source of truth for the LEAL visual system.** Supersedes `DESIGN.md` (v1) and every
> prior draft. The visual language is **ElevenLabs, adopted fully** — warm-cream editorial,
> whisper-weight type, monochrome chrome. Every value below is pinned to the ElevenLabs
> extraction (`reference_elevenlabs.md`) or is a LEAL-specific *structural/data* decision that
> exists because LEAL is a map tool and ElevenLabs is a marketing site. Nothing is left to
> interpretation. There are no imports from other references (no Fraunces serif, no Felt amber,
> no "map-as-hero" language) — those were bolt-ons and are gone.
>
> **Document roles:**
> - **This file** governs. Every value is final.
> - **`reference_elevenlabs.md`** — the source the pinned values came from. Consult it only to
>   confirm an exact hex/px this doc references. It is not an independent instruction set.
> - **`referencesv2.md` / `DESIGN.md`** — historical record of how we got here. Not active
>   instructions. If anything disagrees with this file, **this file wins.**

---

## 0 · What happened, in three sentences (so no one re-opens it)

Earlier passes looked generic because (a) v1 averaged two references into their bland neutral
intersection, and (b) later drafts kept bolting fragments from different references onto each
other (a Felt serif and a Felt amber accent on top of an ElevenLabs foundation), so the system
never actually committed to one coherent language. **The decision is: commit fully to
ElevenLabs.** Warm eggshell paper, whisper-weight Inter, monochrome chrome, color used *only*
where it encodes data — and LEAL's structure (IA, popups, framing) kept exactly as already
approved.

---

## 1 · THE CORE PRINCIPLE (this governs every later decision)

**ElevenLabs is ~97% achromatic warm paper. Chrome carries no decorative color. Color appears
ONLY where it encodes data.**

- The interface — panel, chrome, buttons, borders, type — is **monochrome**: the warm ink→ash
  text ramp on the eggshell→taupe→stone surface stack. Primary actions are **black**, not
  colored (ElevenLabs' explicit rule: "do not introduce colored CTA fills").
- The **only** colors anywhere in LEAL are the **data-encoding colors**: candidate/party
  identity dots, the delta diverging scale, the demographic sequential scale. These are not a
  design choice — they carry meaning, so they earn their color. Everything else is achromatic.
- **There is no UI accent color.** No amber, no violet-chrome, no orange-chrome. ElevenLabs
  reserves its violet/orange for product illustrations only and keeps all UI monochrome; LEAL
  has no product illustrations, so LEAL has no decorative accent at all. This is the cleanest
  possible reading and it is the rule.

If you are ever tempted to add a color to make something "pop," stop — in this system, a thing
pops by being the *only colored (data) element* on a calm monochrome page. That restraint is
the entire aesthetic.

---

## 2 · COLOR TOKENS (pinned, from ElevenLabs)

Add to `index.css` `@theme`. Map ElevenLabs names → LEAL's existing token names so components
don't need renaming.

### 2.1 Surfaces (eggshell → taupe → stone; never pure white, never grey)

```css
--color-bg: #fdfcfc;            /* Eggshell — base canvas, map panel base, button surface */
--color-surface: #f5f3f1;       /* Warm Taupe — cards, expanded panels, popup body, bands */
--color-surface-muted: #ebe8e4; /* Stone — recessed chip fills, icon plates */
--color-border: #ebe8e4;        /* Stone — ALL borders/dividers, 1px */
```

### 2.2 Text (warm ink→ash ramp — this is what makes type read as ink on paper)

```css
--color-text: #000000;          /* Ink — primary text, headings, wordmark, filled buttons */
--color-text-strong: #44403b;   /* Graphite — section labels needing weight */
--color-text-muted: #777169;    /* Smoke — body, muted copy, captions (dominant quiet voice) */
--color-text-faint: #a59f97;    /* Ash — footnote-level: disclaimers, hints */
```

ElevenLabs uses true `#000000` ink and it works *because* the surfaces are warm — the warmth
softens the contrast. We keep pure ink. (This reverses an earlier draft that softened it; on
genuine eggshell it's correct as-is, per the extraction.)

### 2.3 Data colors (the ONLY non-achromatic elements — tuned to sit on warm paper)

These encode meaning and are the sole color in the interface. Tuned so they read cleanly on
`#fdfcfc` eggshell rather than fighting the warm surface:

```css
--color-hugo:   #8B4A9C;  /* plum-violet — warmed from a cold blue-violet so it sits on cream.
                             Still unmistakably "violet," distinct from Felipe/PSD. */
--color-felipe: #1B7952;  /* teal-green — reads well on warm paper as-is, unchanged. */
--color-psd:    #1E3A5F;  /* navy — neutral, reads fine on cream, unchanged. */
```

- **Why Hugo shifted:** a cool `#0447ff`-family blue-violet reads synthetic/cold against warm
  eggshell. `#8B4A9C` (plum) keeps his violet identity while harmonizing with the paper. This
  is the one deliberate hue change, and it's a *data-legibility* fix, not a style whim.
- **Delta diverging scale:** red ↔ teal (NEVER red/green — colorblind safety). Tune both ends
  to warm-paper-legible versions if needed, but the semantic stays loss↔gain.
- **Demographic sequential scale:** indigo ramp. Unchanged semantics.
- These live in `constants.js`; the three identity hexes above are pinned here because Hugo's
  shift must be recorded once, authoritatively.

### 2.4 Explicitly NOT used

- ElevenLabs `--color-violet-spark #0447ff` and `--color-ember-orange #ff4704` — product-
  illustration colors. **LEAL uses neither, anywhere.**
- No amber. No Fraunces. No second accent of any kind.

---

## 3 · TYPOGRAPHY (ElevenLabs system, fully adopted)

ElevenLabs = Waldenburg 300 (display) + Inter 400/500 (everything) + Geist Mono (technical
micro-copy). Waldenburg is not free; ElevenLabs itself names **Inter 300** as its substitute.
So LEAL uses **Inter (300 display / 400–500 functional) + Geist Mono (numbers)**. No serif.

### 3.1 Fonts to load (real webfonts — never system fallback)

```css
--font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
--font-display: 'Switzer', 'Inter', ui-sans-serif, system-ui, sans-serif;
--font-mono: 'Geist Mono', ui-monospace, 'IBM Plex Mono', Menlo, monospace;
```

- `Geist Mono` for all numbers (votes, %, years) — has tabular figures, which LEAL needs for
  column alignment. `IBM Plex Mono` is the acceptable fallback if Geist Mono can't load.
- **No serif font is loaded.** The wordmark is display-face only (see below). This is
  deliberate and final.
- **Wordmark face — Switzer, not Inter.** ElevenLabs' actual display face is **Waldenburg**
  (Dinamo Type), a paid commercial license — not embeddable for free, not a caching issue,
  a real licensing wall. The reference extraction (`reference_elevenlabs.md`) names
  ElevenLabs' own substitute as "Inter (300) or Söhne Light" — Söhne is *also* paid
  (Klim Type Foundry), so Inter was the only free option in that list. Rather than settle
  for Inter twice over (display AND body, which also flags as an overused-face pattern),
  the **wordmark only** uses **Switzer** (Fontshare, free, no license required) — a cold
  Swiss grotesk closer to Waldenburg's actual character than Inter, with a true weight-300
  light. Inter still owns every functional/body role unchanged — that display/body split is
  literally how ElevenLabs itself is built (Waldenburg display + Inter everything else), not
  a compromise. Load via Fontshare: `https://api.fontshare.com/v2/css?f[]=switzer@300&display=swap`.

### 3.2 The whisper-weight move (this is the personality)

ElevenLabs' signature is authority-through-restraint: **weight 300 at large display sizes**,
tight tracking, where everyone else uses 600-700. LEAL's wordmark IS this move:

- **"LEAL" wordmark:** Switzer (see §3.1 — the Waldenburg stand-in), **weight 300**,
  ~34-40px, tracking **-0.02em**. Large, thin, confident on eggshell. Header top padding
  ~20px / bottom ~16px so it breathes.
- Never bold the wordmark. The thinness is the point (ElevenLabs: "bolding destroys it").
- Subtitle ("ANALISE TERRITORIAL / MAPA ELEITORAL — NITEROI"): Inter, 10-11px, weight 500,
  uppercase, +0.06em tracking, `--color-text-muted`. The thin-large ↔ small-tracked contrast is
  the effect.

### 3.3 Full type scale (final — from ElevenLabs, density-adapted for LEAL's compact panel)

| Role | Font | Size | Weight | Tracking | Color |
|---|---|---|---|---|---|
| LEAL wordmark | Inter | 34-40px | **300** | -0.02em | `--color-text` |
| Wordmark subtitle | Inter | 10-11px | 500 | +0.06em, uppercase | `--color-text-muted` |
| Section-title (group label) | Inter | 11px | 500 | +0.06em, uppercase | `--color-text-strong` |
| Panel / popup title | Inter | 14px | 500 | normal | `--color-text` |
| Body / control text | Inter | 13px | 400 | +0.01em | `--color-text` |
| Muted body / caption | Inter | 12px | 400 | +0.01em | `--color-text-muted` |
| Numeric values | Geist Mono | 13px | 400 | tabular | `--color-text` |
| Disclaimer / faint helper | Inter | 11px | 400 | normal | `--color-text-faint` |

Adopt ElevenLabs' **opposite-tracking discipline**: negative tracking on the large-thin
wordmark, slight *positive* (+0.01em) on small Inter body. Relaxed body line-height ~1.5.

---

## 4 · SHAPE, ELEVATION, DENSITY

### 4.1 Radius (ElevenLabs' scale, adapted to a dense instrument)

ElevenLabs uses 20-24px cards and 9999px pill buttons — those are *comfortable-density
marketing* values. LEAL is a compact instrument, so the large radii scale down; the pill stays
only where ElevenLabs' pill genuinely fits (small chips/tags), not on full-width buttons.

| Element | LEAL value | Rationale |
|---|---|---|
| Panel / popup / card container | **12px** | ElevenLabs' 20px softened for a dense panel; still clearly warm-rounded, not sharp. |
| Buttons, inputs, selects | **8px** | ElevenLabs pills full-width buttons; in a dense tool that reads as marketing. 8px is the instrument reading. |
| Chips, tags, year/pair pills | **9999px (full pill)** | This is where ElevenLabs' signature pill lives — small elements. Matches existing `.delta-pair-chip`. |

### 4.2 Elevation (ElevenLabs: borders over shadows; one whisper shadow max)

ElevenLabs prefers **1px hairline borders over drop shadows** and, when a shadow is needed, one
near-invisible whisper. LEAL:

```css
/* the ONE shadow — ElevenLabs' whisper. Use only on the popup (and panel if it needs lift). */
--shadow-panel: rgba(0,0,0,0.4) 0px 0px 1px 0px,
                rgba(0,0,0,0.04) 0px 1px 1px 0px,
                rgba(0,0,0,0.04) 0px 2px 4px 0px;
```

- Everything else separates by **1px stone border** or **tonal stepping** (eggshell→taupe→
  stone), never by shadow. No heavy/blurred shadows anywhere (ElevenLabs "Don't").
- The dominant card pattern is **flat taupe fill on eggshell canvas, no shadow, no border** —
  use this for expanded candidate panels and section bands.

### 4.3 Density (LEAL COMPACT — the one place we hard-override ElevenLabs)

ElevenLabs is explicitly *comfortable* (32px card padding, 96-125px section gaps). LEAL's ~350px
sidebar is *compact*. **Do not use ElevenLabs' spacing.** Use:

- Base unit: 4px.
- Panel padding: **16px**.
- Gap between groups: **12px**.
- Gap between rows in a group: **6-8px**.
- Tight gaps (chip-to-chip, dot-to-label): **4-5px**.
- Card / expanded-panel internal padding: **12-14px**.

Take ElevenLabs' *surface treatment and flatness*; reject its airy marketing spacing. This is
the single most important density rule — if the sidebar feels roomy/landing-page, it failed.

---

## 5 · STRUCTURE & BEHAVIOR (unchanged from v1 — binding)

Visual system aside, these are settled and must not change.

- **Framing discipline (non-negotiable gate).** Never imply individual-voter tracing or vote
  migration. Demographic fields = *composition of the registered electorate at the local*, not
  the candidate's voters. Disclaimer visible when the profile section opens: *"Composicao do
  eleitorado local — nao indica em quem estes eleitores votaram."* Use `Concorrencia`, never
  `Competidor`.
- **Popup structure.** `Candidato` and `Partido` are separate rows (party changes across a
  career). `Cargo pretendido` never dropped from the default view. Delta popup shows both
  endpoints with per-year `Concorrencia` disclosures — never one collapsed "top competitor" row.
- **Sidebar IA (approved per-candidate accordion).** No dropdowns — year, delta-pair, and
  profile-dimension selection are all chips/buttons. Three self-contained candidate rows
  (checkbox = show/hide dots; click name = expand that candidate's own panel with its own year
  chips, Municipal/Geral legend, "Comparar dois anos" toggle). All three independent. Then
  Perfil do Eleitorado, Zonas com Potencial, Filtros (collapsed), Stats (pinned bottom).
- **Do not reintroduce the six-button delta-pair grid.**
- **Interaction states — required.** Every clickable element: visible `:hover` (subtle shift
  toward `--color-surface-muted`, 150-200ms). Every focusable element: `:focus-visible` outline
  **`2px solid var(--color-text); outline-offset: 1px`** — a monochrome (ink) focus ring, since
  there is no accent color; it's crisp on warm paper and fully on-system. ~28-30px min touch
  targets. Maintain mobile behavior (sidebar → constrained upper panel).
- **Stay removed:** `.delta-pair-context` colored `border-left`; `#panel::before` 4-color
  gradient. The panel top is now a plain 1px stone border (no gradient, no accent — monochrome).

---

## 6 · MAP TREATMENT

- The map fills the viewport; the panel is a warm floating overlay on top of it (this is LEAL's
  existing structure — kept, but described in neutral terms, not borrowed "hero" language).
- **Basemap:** must read as credible light **CartoDB Positron** — warm off-white
  (`#fdfcfc`/`#f5f3f1` family) with faint muted street lines. **NEVER a grid/graph-paper
  pattern** (that reads as wireframe). In a static mockup with no real tiles, use a warm solid
  with a few faint organic lines suggesting streets, not geometry.
- **Selected/active local:** since there is no accent color, the active marker is distinguished
  by a **thin ink ring + the whisper shadow**, or a subtle scale-up — monochrome emphasis, not
  a colored halo. The candidate dot keeps its data color; the *selection* affordance is
  achromatic.
- Panel/popup separate from the map by 1px stone border + the one whisper shadow. Elevation by
  tone and hairline, never heavy shadow.

---

## 7 · DESIGN-PASS SCOPE

Structure/IA approved and unchanged. Apply this visual system to `design-mockups.html` **in
place** — static mockup only, no `app-web/`, no `index.css` — until reviewed and approved. Then
a separate pass wires it into React + the real `@theme`.

Steps, in order:
1. Add §2 color tokens + §3.1 fonts to the mockup's token block.
2. Load real Inter + Geist Mono webfonts (Google Fonts). Confirm no system fallback.
3. Wordmark → Inter **300**, 34-40px, -0.02em, with breathing room. All functional text → Inter
   400/500. All numbers → Geist Mono.
4. Apply the warm surface stack (§2.1): eggshell canvas, taupe cards/panels, stone recesses. The
   warmth must be visible — not white, not grey.
5. Apply the warm text ramp (§2.2): ink / graphite / smoke / ash.
6. **Monochrome chrome** (§1): no accent color anywhere. Primary actions black. Data colors
   (§2.3) are the only color, on the map dots / delta / demographic scales only.
7. Compact density (§4.3) — NOT ElevenLabs' comfortable spacing.
8. Radius per §4.1 (12px containers, 8px buttons/inputs, full-pill chips only).
9. Borders-over-shadows (§4.2): 1px stone everywhere; the one whisper shadow only on the popup.
10. Hover/focus states (§5) — ink focus ring.
11. Basemap → warm CartoDB-Positron feel, not graph-paper (§6). Active marker → monochrome ring.

**Must not change:** pipeline, candidate gating, election-pair validity, profile framing,
competitor ranking, sidebar IA, or popup structure.

---

## 8 · SUCCESS TEST (any "no" in 1–7 fails the pass)

1. **Whisper wordmark** — is "LEAL" large, *thin* (Inter 300), and confident? If it looks bold
   or like a normal title, §3.2 failed.
2. **Warm surfaces** — can you see the eggshell→taupe→stone layering? If the panel could pass
   for a generic white admin card, §2.1 failed. *(This test caught every prior failure.)*
3. **Monochrome chrome** — is the interface achromatic except for the data dots/scales? If any
   chrome element (button, border, label, icon) is colored, §1 failed.
4. **Color = data only** — is every colored thing on screen carrying meaning (a candidate, a
   delta, a demographic)? If any color is decorative, §1 failed.
5. **Compact, not airy** — does the sidebar read as a dense instrument, not a spacious landing
   page? If it feels roomy, ElevenLabs' comfortable spacing leaked in — §4.3 failed.
6. **Map reads as a real cartographic surface** — warm Positron, not a wireframe grid (§6).
7. **Framing discipline (non-negotiable gate)** — disclaimer visible, demographic fields labeled
   as electorate composition, `Concorrencia` not `Competidor`. Never traded for aesthetics.

Pass 1-6 and hold 7 → the system is coherent; proceed to React. Any fail → fix in the mockup
first; never carry a failed test into component wiring.

---

## 9 · ONE-LINE SUMMARY (if you read nothing else)

**ElevenLabs, fully: warm eggshell paper, whisper-weight Inter, monochrome chrome, Geist Mono
numbers — and color appears ONLY on the data (candidate dots, delta scale, demographic scale),
never on the interface. LEAL's structure, IA, popups, and framing are unchanged.**
