# P6 Review Taxonomy

**Version:** `P6-RB-1` (`nse/research/journal_taxonomy.py`)  
**Authority:** Rulebook Part 7 Chapter 5 (RB 3708-3774). Owner assigns classifications. Software never auto-grades.

## Outcome classes (process × result)

| Code | Meaning |
|---|---|
| `NOT_REVIEWED` | No owner classification yet |
| `DISCIPLINE_LOSS` | Broke a rule and lost (RB 3748-3750) |
| `PROBABILITY_LOSS` | Followed rules; loss is probability cost (RB 3750-3751) |
| `DISCIPLINE_WIN` | Followed rules and won (RB 3755-3756) |
| `LUCKY_WIN` | Broke a rule but won; still a process failure (RB 3757-3760) |
| `NOT_CLASSIFIED` | Reviewed without choosing a finished Rulebook outcome |

A profitable trade is not automatically good. A losing trade is not automatically a mistake.

## Mistake categories (orthogonal)

`NOT_REVIEWED`, `NONE`, `RULE_VIOLATION`, `EXECUTION`, `PLANNING`, `RISK_MANAGEMENT`, `DATA_LIMITATION`, `PSYCHOLOGY`

## Validation highlights

- `LUCKY_WIN` / `DISCIPLINE_LOSS` require a mistake category other than `NONE`
- `PROBABILITY_LOSS` / `DISCIPLINE_WIN` use `NONE` or `DATA_LIMITATION`
- Optional `rule_refs` are owner citation strings (for example `RB 2139`); the software does not invent Rulebook IDs

## Storage

Append-only `journal_reviews` rows. A later review does not delete earlier ones. Execution facts are unchanged.
