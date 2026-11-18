# P10 Accessibility Review

Method: automated in-page audit on every route in both themes (`run_p10_browser.mjs` → `audit()`), vitest role/label queries, and code review. No assistive-technology session was run; that remains open.

| Check | Result | Evidence |
|---|---|---|
| One `h1` per page, matches nav label | Pass on 20 captures × 2 themes | `results.json` `h1` |
| Buttons have an accessible name (text, aria-label or title) | 0 failures | audit `unnamed_buttons` (first run reported 5 on Journal: labelled buttons inside collapsed `<details>`; audit corrected to `textContent`) |
| Inputs/selects labelled | 0 failures | audit `unlabelled_inputs` |
| Images have `alt` | Pass (attachment preview sets `alt`) | audit `imgsNoAlt` |
| Horizontal page scroll at 390 px | None after fixes | responsive steps |
| Visible focus | 2 px `--gtf-focus` outline on button, a, input, select, textarea, summary, `[tabindex]` in both themes | `global.css` base layer |
| Keyboard | `/` focuses search; Escape closes dialogs/search results/mobile nav; tables accept Up/Down/Enter; dialogs move focus in and restore it | vitest `focuses search with slash`; `Dialog` |
| Landmarks | `nav[aria-label=Primary]`, `header`, `main`, `form[role=search]`, `role=alert` for connection failures | `Shell.tsx` |
| Status not by colour alone | Status badges carry text and a glyph (✓ × • ?), dashed borders for uncertain states; provenance badges carry text; meters always paired with "x of 10" text | `components.tsx` |
| Pressed/selected state | `aria-pressed` on toggles and segmented controls, `aria-current="page"` in nav, `aria-selected` on table rows, `aria-sort` on sorted headers | code |
| Contrast | Computed WCAG ratios: muted text light 5.76:1, dark 5.85:1; primary text 17.51:1 / 15.29:1; warning text on warning background light 5.51:1, dark 9.16:1; primary button text light 8.32:1, dark 7.01:1. Placeholders use the muted token (same ratios). The `--gtf-disabled` token (2.53:1 / 2.90:1) is used only for disabled controls, which WCAG 1.4.3 exempts. Not measured on every component state. | computed from tokens |
| Reduced motion | Animations and transitions disabled under `prefers-reduced-motion` | `global.css` |

Open items (Minor): no screen-reader session; no automated contrast scan across all states; the chart canvas is not described beyond its legend and the textual evidence/zone/plan panels (unchanged from P2).
