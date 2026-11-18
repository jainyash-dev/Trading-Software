# Design system and navigation

Updated 2026-11-17 for P10. Detail: [P10 design system](../../../docs/implementation/p10/P10_DESIGN_SYSTEM.md) and [P10 information architecture](../../../docs/implementation/p10/P10_INFORMATION_ARCHITECTURE.md).

Light status colours match [the frontend specification](../../../docs/product/FRONTEND_SPECIFICATION.md); dark uses same-hue lighter values. Dark is the default; the header switch and Settings › Appearance change it, the choice persists in `localStorage` (`gtf-theme`) and `public/theme-init.js` applies it before first paint. Status chips keep a text label and a glyph. Green and red are for price direction and pass/fail text, not for a buy button.

Navigation groups are Overview, Research, Trading, Intelligence and System (18 destinations). Routes without a backend show a capability page and a `Later` tag; routes with part of a capability missing show `Partial`. Below 1100 px the sidebar collapses to icons and the label stays available to assistive technology. `/` focuses search. Escape blurs the active control and closes dialogs.

Empty, loading, and disconnected states are separate from fixture specimens. Fixture specimens appear only after "Show fixture specimens" or `?fixtures=1`, and the banner reads `FIXTURE_NOT_MARKET_DATA`.
