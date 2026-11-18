# P10-2 Design System

Files: `platform/web/src/styles/global.css` (tokens), `src/design/components.tsx` (components), `src/design/format.ts` (display formatting), `src/layout/icons.tsx` (icons), `public/theme-init.js` (pre-paint theme).
No new dependency. No Ant Design (not present in this repository). System font stack; tabular numerals for all figures.

## Tokens (both themes share names; values differ)

| Token | Use | Light | Dark |
|---|---|---|---|
| `--gtf-canvas` | app background | `#eef1f5` | `#0a0e13` |
| `--gtf-surface` / `-surface-2` / `-elevated` | panels / table heads / dialogs | `#fff` / `#f6f8fa` / `#fff` | `#10151c` / `#151b23` / `#1a212b` |
| `--gtf-line` / `-line-strong` | dividers / input borders | `#e1e5ea` / `#c9d1da` | `#222a35` / `#323c49` |
| `--gtf-ink` / `-ink-2` / `-muted` / `-disabled` | text tiers | `#141a21` / `#36424f` / `#5c6773` / `#9aa4ae` | `#e6ebf1` / `#b8c2cd` / `#8693a2` / `#56616d` |
| `--gtf-accent`, `-accent-bg`, `-focus`, `-selection` | primary action, selected nav, focus ring, selected row | `#1f4b99` … | `#6d9bf1` … |
| `--gtf-ok` / `-fail` / `-manual` / `-info` (+ `-bg`) | positive / negative / warning / informational | spec values (`#1d6b3a`, `#8f2d2d`, `#8a5a00`) | lighter same-hue equivalents |

Status colours in light mode keep the frontend-specification values. Chart price-direction colours follow the theme (`chartPalette` in `CandleChart.tsx`); zone and plan overlay colours are unchanged.

CSS resets (`button { color: inherit }` etc.) live in `@layer base` so utility colours win. Found during P10 light-theme review: unlayered resets had overridden every button text colour.

## Typography and layout

Page title 19 px semibold; section 13 px semibold; body 12.5-13 px; table 12 px; meta 11-11.5 px; eyebrow 10.5 px uppercase tracking. Spacing 4/8/12/14/16/20 px. Radius 3-6 px. Sidebar 232/56 px, top bar ≥48 px, page gutter 20 px. Breakpoints: Tailwind `md` 768, `lg` 1024, `xl` 1280, `2xl` 1536; navigation compacts at 1100 px. Dialog max 28 rem. Long codes wrap (`overflow-wrap: anywhere`) so no page scrolls horizontally at 390 px; dense tables scroll inside their own container.

## Components

`Page` (eyebrow, h1, description, meta, actions) · `Panel` · `Metric` (null value → "Unavailable" text (em dash plus word), never 0) · `Meter` (decorative; text carries "x of 10") · `KeyValue` · `StatusBadge` (text + glyph ✓ × • ?, dashed border for uncertain states) · `ProvenanceBadge` (`CERTIFIED`, `PROVISIONAL`, `EXPLORATORY · NOT CERTIFIED`, `FIXTURE`, `STALE`, `UNAVAILABLE`, `NOT_IMPLEMENTED`, `BLOCKED`, `PARTIAL`, `CONNECTED`) · `Callout` · `Notices` (collapsible group; every notice stays in the DOM) · `EmptyState` · `Skeleton` · `TextInput` / `SelectInput` / `Checkbox` / `Switch` · `Segmented` (aria-pressed group) · `DataTable` (field sort with `aria-sort`, keyboard cursor, numeric right-alignment) · `Dialog` (focus moves in, Escape closes, focus restored) · `Button` (default / primary / ghost / danger; sm / md). Shared feature UI (`Section`, `Fact`, `Warning`, `ErrorLine`, `JobState`, `Completeness`) restyled on the same tokens.

## Formatting (`format.ts`)

`formatInr` (₹ with Indian grouping, 2 dp), `formatPrice` (as returned, ≤4 dp), `formatQuantity`, `formatPaise`, `formatPercent`, `formatDate`. Every helper returns `null` for a non-number so callers render Unavailable. They format API values only; no figure is derived.

## Theme

Header switch and Settings › Appearance. Preference in `localStorage` (`gtf-theme`, display only; storage errors are tolerated). `theme-init.js` sets `data-theme` before first paint (browser check: `light` at DOMContentLoaded after reload). Chart follows theme changes without re-creation (MutationObserver).

## Validation

Specimens of every status and provenance label: Settings › Status vocabulary (both themes in `evidence/p10-browser/shots/*-settings.png`). The two `CERTIFIED` badges counted by the browser audit are these specimens only.
