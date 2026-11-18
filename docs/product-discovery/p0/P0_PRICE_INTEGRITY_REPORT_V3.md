# P0 price integrity report (V3)

**Date:** 2026-11-15. No price was adjusted, repaired or deleted. Register: `P0_PRICE_EXCEPTION_REGISTER_V3.csv` (1,132 member-dates outside `CONTINUOUS`).

## 1. Price-continuity gate (isolated build F, identical to E)

| Value | Member-dates | Classification |
|---|---|---|
| CONTINUOUS | 122,646 | - |
| PREVCLOSE_BREAK_ACROSS_EXCLUDED_SESSION | 700 | Owner decision Q7 (OD-PX-4) |
| NO_EQ_ROW | 383 | Must remain excluded (BE-only 260; dummy 123) |
| PRICE_SCALE_EVENT_ON_STEP | 39 | Explained by a recorded NSE event; completeness unproved (D66) |
| PRIOR_SESSION_NON_EQ:BE | 4 | Must remain excluded (previous close comes from a BE row) |
| ISIN_CHANGE_ON_STEP | 3 | Explained by a recorded event |
| STEP_ACROSS_EXCLUDED_SESSION | 2 | Requires more evidence (HDFCBANK 2024-03-04; TATACONSUM 2024-05-21; both on OD-PX-4 dates) |
| UNEXPLAINED_PRICE_SCALE_GAP | 1 | Owner decision Q9 (ADANIENSOL) |

## 2. ED-57: VBL 2.5x split (authorised, implemented)

- Exact rational parsing (`face_value_ratio`): Decimal and Fraction; old:new share counts in lowest terms; fail-closed cases tested.
- VBL 2024-09-12 is now `SPLIT 2:5` in `actions.csv` (single line). Held parity: 2,064 of 2,064 rows re-derive identically.
- Effect: VBL's 678 member-dates move from `UNPARSED_EVENT` to `EVENTS_VERIFIED_COMPLETENESS_NOT_PROVED`. Price continuity on the step is still `PRICE_SCALE_EVENT_ON_STEP` (it now names SPLIT). OHLC is unchanged. **Certified count unchanged (0).**
- Independent review: PASS_WITH_FINDINGS. Three changed test expectations await the owner's sign-off (queue V4).

## 3. ADANIENSOL 2024-11-21 (Q9 pending): decision pack

| Check | Evidence (held) | Result |
|---|---|---|
| Raw OHLC | `BhavCopy_NSE_CM_0_0_0_20241121_F_0000.csv.zip`: prev 871.55, open 697.25, **high 724.00**, low 697.25, close 697.25 | open = low = close = 0.8000 x prev (lower 20% band at the 0.05 tick) |
| Previous close chain | 2024-11-19 close 871.55 = 2024-11-21 prev (2024-11-20 not a session); 2024-11-22 prev 697.25, close 648.95 | Chain intact |
| Corporate action | Held NSE API body for ADANIENSOL, Jun 2024-Mar 2025: only an AGM | No price-scale event recorded |
| Circuit-band file | Not held; not retrieved (not authorised) | Band inferred from the price arithmetic only |

Assessment: consistent with a market move to the 20% lower band, not an adjustment or a data error. It remains an unresolved anomaly under current rules. Options for the owner: (a) keep excluded (default); (b) create a reviewed market-move exception requiring price-band evidence, an intact previous-close chain and the absence of a CA record. Earlier documents described this session as open = low = close; the high was 724.00 (corrected here).

## 4. OD-PX-4 (Q7 pending): shortened-session previous-close analysis

| Break date | Member-dates | Preceding excluded session (held archive; calendar `CONFIRMED`) |
|---|---|---|
| 2021-11-08 | 99 | 2021-11-04 Diwali Muhurat (NSE/CMTR/50050) |
| 2022-10-25 | 100 | 2022-10-24 Muhurat (NSE/CMTR/54023) |
| 2023-11-13 | 101 | 2023-11-12 Muhurat (NSE/CMTR/59124) |
| 2024-03-04 | 100 | 2024-03-02 Special live session with DR switch-over (NSE/MSD/60677) |
| 2024-05-21 | 100 | 2024-05-18 Special live session with DR switch-over (NSE/MSD/61893) |
| 2024-11-04 | 100 | 2024-11-01 Muhurat (NSE/CMTR/64628) |
| 2025-10-23 | 100 | 2025-10-21 Muhurat (NSE/CMTR/70319) |
| **Total** | **700** | |

Current logic: the session after an excluded (held but non-regular) session fails the price gate because the previous close refers to the excluded session. Proposed rule (not adopted): pass it when the chain is intact through the held excluded session's EQ row. Risks: it treats a one-hour Muhurat print as a valid price anchor, and that would apply to zone inputs too. Even if adopted, all 700 still fail D66.

## 5. BRITANNIA 2021-05-25 and TVSMOTOR 2025-08-25 (Q8 pending)

| Event | Original terms (saved NSE subject) | Price step (held bhavcopy) | Nature |
|---|---|---|---|
| BRITANNIA | "Scheme Of Arangement- Bonus - 1 Debenture For 1 Equity Share Held" (+ Rs 12.50 dividend) | 3,379.10 -> close 3,439.50; no scale break | Distribution of a debt security; equity share count unchanged |
| TVSMOTOR | "Scheme Of Arrangement - Bonus Ncrps 4:1" | 3,294.60 -> 3,284.70; no scale break | Bonus non-convertible redeemable preference shares; equity share count unchanged |

Approaches: (a) keep unparsed (default; the two steps stay excluded); (b) classify as a non-price-scale distribution like a dividend (R-12), which needs an owner rule. A value transfer still occurs; its size is not quantified here. No classification was implemented.

## 6. CGPOWER 2016-03-15 (Q11 retrieval done)

Held: NSE/FAOP/31828, NSE/CMTR/31832, NSE/FAOP/31970, and the **CGCEL Information Memorandum dated 2016-05-06** (issuer document on the NSE archive; SHA-256 `a4123d0f...`). The IM states the scheme was sanctioned by the Bombay High Court on 2015-11-20, with appointed date 2015-10-01, effective date 2016-01-01 and record date 2016-03-16, and that "the share entitlement ratio being 1:1". Classification: **demerger, entitlement 1:1, no price factor** (the price was set by a special pre-open session; contracts were re-listed without an adjustment factor). The entitlement is not a price ratio, so no split factor applies. The event stays `UNPARSED_PRICE_EVENT` (pre-window). No parser or data change was made; closing the exception would need an owner rule on demerger representation.
