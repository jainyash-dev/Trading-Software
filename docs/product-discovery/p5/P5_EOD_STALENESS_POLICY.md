# P5 EOD Staleness Policy

**Status:** Engineering policy for GTF P5 portfolio valuation (PR-007 / FR-6.3)  
**Date:** 2026-11-16  
**Authority:** Engineering discretion under existing FR-6.3; not a methodology change

## Policy

1. Valuation uses the last accepted local daily close with trade date on or before the valuation date.
2. The actual session date of that close is always exposed as `price_date`.
3. When `price_date` equals the valuation date, the mark state is `AVAILABLE`.
4. When `price_date` is earlier than the valuation date, the mark state is `STALE`. The close is still usable.
5. There is **no** maximum-age threshold in P5. An older accepted close is not rejected solely because it is old.
6. A future session close is never used.
7. Missing, invalid, NaN/Inf, or unusable marks remain `UNAVAILABLE`. Prices are never invented or interpolated.
8. An EOD mark is never described as a live quote. Live quotes remain out of scope.
9. Sector concentration and live drawdown remain `UNAVAILABLE` (D6 / FR-6.7 / PR-009 exclusion).

## Owner decision reserved

A future maximum-age cutoff (for example, refuse marks older than N sessions) requires an explicit owner-approved decision. Until then, P5 keeps STALE marks visible and usable with their real `price_date`.
