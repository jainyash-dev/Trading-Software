---
name: database-engineering
description: Change or operate the optional SQLite research store and paper-trade journal (nse/research/store.py): additive versioned migrations with checksums, idempotent scan import, zone history queries, backups, and the journal's Rulebook constraints. Use for any schema change, store import problem, journal question, or before relying on stored history.
---

# Research store and journal

The JSON/CSV reports are the primary record. The store keeps them queryable over time; it
never recomputes or changes a decision.

## Run

```
python3 -m nse.research.cli store-import --db nse/output/research.db --scan nse/output/scan/scan.json
python3 -m nse.research.cli store-zone-history --db nse/output/research.db --symbol <S> --zone <ZONE_ID>
python3 -m nse.research.cli store-backup --db nse/output/research.db --dest nse/output/research-backup.db
python3 -m nse.research.cli journal-summary --db nse/output/research.db --month 2026-11
python3 -m nse.validation.run_all --group store
```

## Schema changes

1. Append a new migration; never edit an applied one (its checksum is recorded and drift
   raises). Migrations are additive: no DROP, no DELETE, no UPDATE without WHERE.
2. Add a test that applies every migration to an empty file and to the previous version.
3. Back up (`store-backup`, refuses to overwrite) before migrating a real store.

## Journal rules (Rulebook)

- Entries only for candidates the stored scan shows as ACTIONABLE (manual checks pending)
  or MANUAL_REVIEW with a written resolution; never REJECTED, BLOCKED or DATA_INSUFFICIENT.
- Every manual checklist item is explicitly confirmed; the SL never changes after
  TRIGGERED (RB 2139); there is no add-to-position event (RB 2140); STOP_LOSS_HIT and
  ZONE_INVALIDATED are separate events (R4); 10 trades per month is the ceiling (RB 2392).
- The journal records the owner's decisions. It places no order and connects to no broker.

## Verification

`tests/test_research_store.py` passes; `store-import` of the same scan twice reports
ALREADY_PRESENT; status counts in the store reconcile with `summary.json`.
