---
name: adversarial-testing
description: Try to make the research system wrong. Use after any change that could produce a false-positive candidate, bypass a safety gate, lose a manual-review flag, leak future data or overstate validation, and periodically as a regression sweep.
---

# Adversarial testing

## Run

```
python3 -m nse.validation.run_all --group adversarial --group lookahead
```

## The questions (tests/test_research_adversarial.py names them q1-q14)

1. Can a tested zone appear in the fresh-zone report?
2. Can an invalidated zone become a candidate?
3. Can missing history be read as freshness?
4. Can a raw engine assessment bypass the MTF overlay?
5. Can a manual-review requirement vanish in JSON or CSV?
6. Can a failed G0 be overridden by a later gate?
7. Can an intraday (WIT) candidate appear while intraday is blocked?
8. Can future candles change an earlier decision? (lookahead tests)
9. Can missing higher-timeframe data read as "no conflict"?
10. Can a report claim external validation from unit tests?
11. Can a missing reference produce a successful comparison?
12. Can an unresolved rule acquire a default?
13. Can equivalent scans disagree?
14. Can a test pass without exercising its path? (mutation canaries patch a gate off and
    require the outcome to change)

## Method

Make the engine and the overlay disagree (engine ELIGIBLE, overlay TESTED), make the
future disagree with the past, remove one input at a time, and sweep random walks
(`_research.random_walk`) for invariants. Every confirmed defect becomes a regression test
before the fix. Prioritise false-positive candidates over cosmetic issues.
