---
name: strategy-gate-validation
description: Validate the G0-G8 qualification gates and candidate statuses in nse/research/qualification.py. Use for any change to location, trend, the alignment matrix, HTF conflict, coinciding, trade levels, red flags, status derivation or MIT/WIT roles.
---

# Strategy gate validation

## Run

```
python3 -m nse.validation.run_all --group strategy_gates --group adversarial
python3 -m unittest -v test_research_gates          # from tests/, for detail
```

## How the tests are built

`tests/_research.py` `ideal_mit_builder()` is a SYNTHETIC snapshot in which every automated
gate passes (status ACTIONABLE CANDIDATE: MANUAL CHECKS PENDING). Each gate test changes
one input. For every gate keep cases for: pass, fail, missing input (DATA_INSUFFICIENT),
ambiguous input (MANUAL), and an interaction with another gate.

## Rules to hold

| Gate | Must be true |
|---|---|
| G0 | Data errors or a truncated execution series stop everything; no calendar is MANUAL; WIT is BLOCKED |
| G1 | Only overlay-kept zones; demand; test_count 0; WIT recency 8 / 9-10 / >10 / >20 bands |
| G2 | ELIGIBLE -> PASS; engine MANUAL_REVIEW -> MANUAL; nothing below 7/7 is evaluated |
| G3 | Curve from FRESH M (MIT) or W (WIT) zones; tested boundary skipped; unknown boundary MANUAL; VHOC FAIL; HOC MANUAL |
| G4 | MIT gate = Weekly, Monthly context only (D21); WIT gate = Daily only (D22); < 55 candles MANUAL; truncated DATA_INSUFFICIENT |
| G5 | Fresh M/Q/HY inside or <= 5% FAIL; 5-10% MANUAL; W/Y within 10% MANUAL; missing M/Q/HY DATA_INSUFFICIENT |
| G6 | Inside a DL-untouched HTF DZ PASS; below its DL FAIL; above its PL MANUAL |
| G7 | R:R >= 2 for every buffer/SL choice PASS; < 2 for all FAIL (RF8); else MANUAL; no fresh target MANUAL |
| G8 | RF3 clear down not at VLOC FAIL; RF7, EC1, EC7 MANUAL when undetermined |

Status = most restrictive outcome (`models.derive_status`). A later PASS never overrides an
earlier FAIL. MIT and WIT differences need their own tests.

A new rule needs a source (RB line or D number). If none exists, the case is MANUAL and the
question goes to the blockers document.
