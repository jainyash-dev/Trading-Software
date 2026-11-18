# P0 Milestone 2 Preflight Audit

**Title:** Corporate-action completeness, membership backlog and certification governance  
**Prepared:** 2026-11-15  
**Scope:** Read-only preflight. No Milestone 2 implementation. No owner decisions written. No evidence acquired. No commits or pushes.  
**Governance chair:** `gtf-autonomous-project-lead`  
**Specialists consulted (skill text applied to repository evidence):** `gtf-p0-data-certification`, `gtf-quantitative-validation`, `gtf-production-readiness`  
**Authority reminder:** Rulebook > owner decisions in exact scope > Pine (non-conflicting silence) > project lead > specialists > procedure skills > advisory council. Handoff recommendations are not owner decisions. R-5 remains unresolved.

---

## 1. Executive verdict

**Final status: `PREFLIGHT_BLOCKED`**

The corporate-action completeness gate as coded can mark a symbol/date window `CA_COMPLETENESS_VERIFIED` or `COVERED_NO_EVENTS_PROVED` from **one** hash-verified non-API source file plus a matching `USER_APPROVED` decision-log acceptance line. The Milestone 2 handoff's intended standard - two independent official sources reconciled event-by-event - is **not** enforced in schema, loader, builder or tests.

Membership backlog counts (24 evidence-sufficient / 14 insufficient / 25 not-applicable) **reconcile**. Nine backlog rows show `ACCEPT_RECOMMENDED` with `EVIDENCE_INSUFFICIENT`; that is a field-model conflation (membership vs identity/EQ), not ledger corruption. It does not by itself block Milestone 2 once fields are separated in process.

Nothing is certified today (`completeness.csv` absent; 0 certified member-dates). The block is procedural: implementing Milestone 2 against the current gate would allow incomplete independent evidence to certify.

| Label | Verdict |
|---|---|
| Audit A (CA completeness gate) | **`FAIL`** - single approved source file can pass |
| Audit B (membership backlog) | Reconciles; contradictions are classification conflation |
| Audit C (dataset scope integrity) | Fail-closed gates preserved on disk; ~175 periods is dry-run only |
| Single-source loophole | **Exists** |
| Milestone 2 implementation may begin | **No** - close the gate gap first (or get an explicit owner decision that one independent source is the acceptance bar) |

---

## 2. Actual repository baseline and Git state

**Verified fact** (recomputed 2026-11-15 from files on disk; not assumed from the handoff):

| Item | Handoff baseline | Actual now |
|---|---|---|
| HEAD | `69858d0` + dirty tree | `69858d0` (`docs: close remaining GTF governance reconciliation gaps`); branch `main` ahead of `origin/main` by 17 |
| Builder | 1.5.0 | 1.5.0 (`P0_CERTIFICATION_SUMMARY.json` `build_version`) |
| Member-dates | 123,778 | 123,778 |
| Certified | 0 | 0 (`certified_symbol_dates`) |
| Exploratory only | 73,366 | 73,366 (`research_use.EXPLORATORY_ONLY_NOT_CERTIFIED`) |
| Membership periods verified | 85 of 185 | 85 of 185 |
| Ledger | 140 `ACCEPTED`, 131 blank; SHA-256 `9b0fcba0…` | Confirmed: 140 / 131; SHA-256 `9b0fcba06cc57761a4adbf0a938e004fb6adf808ba7724842248977391ec1f39` |
| `completeness.csv` | absent; 0 windows | absent under `nse/data/corporate_actions/`; `completeness_register.present=false`, `proved_windows=0` |
| CA tiers | (handoff) | `CA_RESPONSE_PRESENT_NOT_COMPLETE` 108,323; `CORPORATE_ACTIONS_UNVERIFIED` 15,455 |
| Rows passing every data gate | 0 | 0 |
| Commits/pushes this audit | n/a | **None** (read-only) |

**Doc drift (fact):** `P0_REMAINING_BLOCKERS.md` still says exploratory **73,368**, CA middle tier **108,325**, and cites builder **1.1.0**. Tracker/handoff/summary agree on **73,366** / **108,323** / **1.5.0**. Severity: LOW (documentation), not a certification-math break (`reconciliation` all true in the summary).

**Git:** Large dirty working tree (Milestone 1 uncommitted work). This audit created only this report file. No staging, commit or push.

---

## 3. Governance and authority verification

| Check | Result |
|---|---|
| `CLAUDE.md` authority order | Applied; Rulebook first; R-5 unresolved |
| Decision log through last headings | D62-D65 read; latest membership acceptance is D65 (batch 2 only). OD-CA-1 still open |
| `gtf-autonomous-project-lead` | Chair for this audit |
| `gtf-p0-data-certification` | Scope owner for completeness/membership/identity evidence |
| `gtf-quantitative-validation` | Sample-integrity implications of premature certification |
| `gtf-production-readiness` | Reproducibility / fail-closed / traceability of certification outputs |
| Handoff "ACCEPT_RECOMMENDED" / "EVIDENCE_SUFFICIENT_…" | **Not** treated as owner approval |
| `USER_STATED` / `PROPOSED` | Not treated as completeness approval (code + log parsing agree) |
| Agents writing ledger `ACCEPTED` | Still owner-reserved (D49/D53/ED-27/ED-35/ED-48; P0 skill §4.2) |

**Finding G1 - Severity MEDIUM**  
**File:** `docs/product-discovery/p0/P0_MILESTONE2_HANDOFF.md` §C vs `nse/docs/DECISION_LOG.md` D62  
**Evidence:** D62 approves evidence *tiers* and forbids inferring completeness from PREVCLOSE / weak responses. It does **not** bind "two independent sources reconciled event-by-event". That two-source bar is a handoff **recommendation**.  
**Consequence:** Without an owner decision stating the acceptance bar, implementers could treat the coded one-source register as "D62-complete".  
**Correction:** Owner records whether OD-CA-1 requires dual-source reconciliation or a single independent non-API source under the existing marker line. Until then, treat the handoff's dual-source bar as the conservative preflight standard (this audit's A1).

---

## 4. Corporate-action completeness gate audit

### Enforcement path (fact)

1. `p0_certification.build()` loads `completeness.csv` via `corporate_actions.load_completeness(..., completeness_decisions(decision_log), api_hashes)` (`p0_certification.py` ~471-475).  
2. `completeness_decisions` keeps only `USER_APPROVED` decisions whose own entry contains `- **Completeness source accepted:**` items of form `<sha256> <SYMBOL> <from>..<to>` (`corporate_actions.py` 351-381).  
3. A register row counts only if: decision id matches `D\d+`; item matches accepted set; cited file is **not** a saved API response (`_is_saved_api_response`); `source_verified` hash matches (`load_completeness` 404-439).  
4. `_ca_value` passes the CA gate only when `completeness_proved` **and** hash-verified body with no unparsed price subject: empty → `COVERED_NO_EVENTS_PROVED`; parsed integrity statuses → `CA_COMPLETENESS_VERIFIED` (`p0_certification.py` 243-279).  
5. `evidence_tier(..., completeness_proved=True)` yields `CA_COMPLETENESS_VERIFIED` for those statuses (`corporate_actions.py` 309-318).

### What is enforced well (fact)

- Missing register → empty → nothing certifies (today's real state).  
- API responses (`ca_*.json`, `raw/`, byte match to API hashes, or API JSON shape with `exDate`) cannot be the completeness source.  
- `USER_STATED` / `PROPOSED` / id-only / wrong hash / wrong symbol / wrong window rejected.  
- Renamed-away / ambiguous tickers' responses and renamed empty `[]` fail closed.  
- Unparsed price subjects never pass.  
- Unverified body hashes never pass even with a register window.  
- Tests: `tests/test_research_p0_certification.py` (`CompletenessRegister`), `tests/test_research_p0_build_e2e.py` (61 tests passed this audit).

### What is not enforced (fact) relative to intended dual-source standard

| Intended rule (audit brief / handoff §C recommendation) | Code |
|---|---|
| Two independent official sources | Schema has **one** `source_file` / `source_sha256` |
| Both held locally with SHA-256 | Only one file checked |
| Event-by-event reconcile (type, ex-date, ratio) | **No** reconciliation function |
| Disagreements recorded as conflicts | **No** conflict register for dual sources |
| Owner approves exact reconciliation of both | Marker names **one** hash per item |

**Audit A conclusion: `FAIL`**

---

## 5. Single-source loophole result

**Answer: YES - one approved source file alone can cause `CA_COMPLETENESS_VERIFIED` or `COVERED_NO_EVENTS_PROVED`.**

| Element | Evidence |
|---|---|
| Function | `corporate_actions.load_completeness` continues a row after a single `source_verified` check; no second source required |
| Gate | `p0_certification._ca_value` returns `de.CA_COMPLETE` / `de.CA_COVERED_NONE` when `completeness_proved` is true for that one window |
| Tests that prove single-source sufficiency | `CompletenessRegister.test_the_gate_value_needs_a_proved_window`; e2e fixture writes one `proof` file per symbol and certifies AAA/DDD |
| Tests for dual-source reconciliation | **None** |

**Severity: CRITICAL**  
**Consequence:** Milestone 2 could certify member-dates on a single non-API extract that is incomplete or silently omits events (the same class of risk R-10 / R-12 residual was meant to close).  
**Minimum safe correction (recommendation; not implemented here):**

1. Extend completeness evidence to two independent source files (hashes, paths, provenance).  
2. Require automated or recorded event-level reconciliation (type, ex-date, ratio); any mismatch → fail closed.  
3. Decision-log marker must name **both** hashes (and symbol/window) under `USER_APPROVED`.  
4. Regression tests for every adversarial case in §6 that is currently untested for dual-source behaviour.  

**Alternative (owner decision required):** Explicitly accept the current one-source + marker design as OD-CA-1's bar, and update the handoff so "two sources" is no longer the stated requirement. Until that decision exists, treat dual-source as required for preflight pass.

---

## 6. Adversarial test matrix and results

Legend: **Reject** = current code refuses / does not prove; **Pass risk** = can reach verified/covered tiers; **Untested** = no dedicated test exercising the production path.

| Case | Result | Evidence | Severity |
|---|---|---|---|
| One source accepted, second absent | **Pass risk** (by design of current schema) | Single-column register; e2e certifies with one proof file | CRITICAL |
| Two files that are copies of the same source | **Untested / Pass risk** if only one is cited | No independence check between two cited sources (second not required) | CRITICAL |
| Same source via two URLs | **N/A / Pass risk** | Only one path stored; URL duplication not modelled | HIGH |
| Source hash mismatch | **Reject** | `source_verified` fail → row ignored; tested | - |
| Wrong symbol | **Reject** | Acceptance item must match symbol; tested | - |
| Wrong date window | **Reject** | Item dates must match; tested | - |
| Missing events in one of two sources | **Untested / Pass risk** | No event reconciliation | CRITICAL |
| Different ex-dates across sources | **Untested / Pass risk** | No event reconciliation | CRITICAL |
| Different event ratios | **Untested / Pass risk** | No event reconciliation | CRITICAL |
| Unparsed price subjects | **Reject** | `_ca_value` keeps `UNPARSED_EVENT`; tested | - |
| Saved API response as completeness source | **Reject** | name / `raw/` / bytes / `exDate` shape; tested R-3 | - |
| Empty API `[]` as proof of no events (no register) | **Reject** | `EMPTY_RESPONSE` never passes alone; tested | - |
| Empty `[]` **with** register window | **Pass as `COVERED_NO_EVENTS_PROVED`** | Intended once completeness proved; dangerous if proof is single-source incomplete | CRITICAL (under dual-source bar) |
| Old / ambiguous ticker response | **Reject** | `CA_OLD_TICKER`; tested | - |
| Renamed ticker empty response | **Reject** | `CA_EMPTY_RENAMED`; tested | - |
| Decision id without exact marker items | **Reject** | tested R-2 / R2-A / R2-B | - |
| `USER_STATED` / `PROPOSED` as approval | **Reject** | `completeness_decisions` filters `USER_APPROVED` only; tested | - |

**Distinction:** Unit/e2e tests exercise real `load_completeness` / `_ca_value` / `build()` paths (not docs). They **prove** single-source certification works. They do **not** prove dual-source safety.

---

## 7. Membership backlog reconciliation

**File:** `docs/product-discovery/p0/P0_MEMBERSHIP_BACKLOG.csv` (131 rows = all blank ledger decisions).

| Metric | Handoff | Recomputed |
|---|---|---|
| Undecided ledger rows / backlog rows | 131 | 131 |
| Groups total | (implied) | 63 |
| Evidence-sufficient groups | 24 | **24** |
| Evidence-insufficient groups | 14 | **14** |
| Not applicable (count groups) | 25 | **25** |
| Ledger ACCEPTED / blank | 140 / 131 | 140 / 131 |
| Periods verified today | 85 / 185 | 85 / 185 |
| Projection if 24 accepted | ~175 (dry run) | **Not re-simulated** this audit; handoff labels it dry-run / scratch copy. Union of "periods if alone" strings = 72 period strings (under-counts periods that need later groups) - consistent with needing a cumulative dry-run, not a certified outcome |

Source hashes for all 24 sufficient groups were recomputed against files on disk: **all match** backlog `source_sha256`.

---

## 8. Contradictory recommendation/classification register

**9 rows** with `recommendation_on_file = ACCEPT_RECOMMENDED` and `classification = EVIDENCE_INSUFFICIENT`:

| Group | Symbol(s) | Root cause (fact) | Conflated question |
|---|---|---|---|
| G-BASELINE-2020-12-31 | BAJFINANCE, GRASIM | Baseline list names them; identity unresolved (OD-ID-1/2) | Membership list vs identity |
| G-R-2023-08-21-JIOFIN | JIOFIN | Dummy→listed rename; no EQ on old/boundary | Membership vs EQ data |
| G-R-2025-01-29-ITCHOTELS | ITCHOTELS | Same class | Membership vs EQ |
| G-R-2025-06-19-ENRIN | ENRIN | Same class | Membership vs EQ |
| G-R-2025-11-12-TMCV | TMCV | Same class | Membership vs EQ |
| G-E16 | ITCHOTELS REMOVE | Release agrees; no EQ boundary | Membership vs EQ |
| G-E19 | ENRIN REMOVE | Same | Membership vs EQ |
| G-E22 | TMCV REMOVE | Same | Membership vs EQ |

**Additional non-row contradiction (same CSV model):**  
`G-I-2024-09-12-VBL` is classified `EVIDENCE_SUFFICIENT_OWNER_DECISION_REQUIRED` but recommendation `INSUFFICIENT_EVIDENCE` because the 5-to-2 split is unparsed (OD-PX-2). Membership evidence and price-parser representability are different questions.

**Impact:** HIGH for owner packaging clarity; **not** evidence that the ledger was wrongly written. Do not auto-flip recommendations. Keep membership acceptance separate from identity verification and from EQ research eligibility (handoff §A "Series and membership are separate" - verified fact in converter behaviour).

**Severity:** MEDIUM (process / data model).  
**Correction:** Split fields (§9); owner packs should show four statuses per group.

---

## 9. Proposed membership / identity / EQ status model

**Recommendation only - CSV/ledger not changed.**

| Field | Permitted values | Meaning |
|---|---|---|
| `membership_evidence_status` | `SUFFICIENT` / `INSUFFICIENT` / `NOT_APPLICABLE` | Official index evidence for the membership row |
| `identity_evidence_status` | `RESOLVED_VERIFIED` / `AMBIGUOUS` / `UNKNOWN` / `NOT_REQUIRED` | Symbol/ISIN point-in-time identity |
| `eq_data_status` | `EQ_BOUNDARY_OK` / `NON_EQ_ONLY` / `NO_ROW` / `NOT_CHECKED` | Trading-series availability for research prices |
| `owner_membership_recommendation` | `ACCEPT_RECOMMENDED` / `REJECT_RECOMMENDED` / `DEFER` / `N/A` | Advice only |

**Transitions:**  
`membership_evidence_status=SUFFICIENT` may move to ledger `ACCEPTED` only by owner. That must **never** set identity to resolved or `eq_data_status` to EQ. Certified research still requires all six data gates.

**Worked examples:**

| Case | membership | identity | eq_data | Owner membership action | Research dates |
|---|---|---|---|---|---|
| Dummy→listed rename (JIOFIN etc.) | May be SUFFICIENT from release | Placeholder may stay UNKNOWN | `NON_EQ_ONLY` / `NO_ROW` on dummy | May ACCEPT membership | BE dates stay EOD-fail |
| BE-only listings | SUFFICIENT possible | May resolve on listed ticker | `NON_EQ_ONLY` | ACCEPT ≠ EQ use | Excluded by EOD gate |
| ENRIN / TMCV | As above | - | BE stretches | Optional ACCEPT | Fail EOD / stay excluded |
| VBL 2024-09-12 | SUFFICIENT (ISIN change evidenced) | Resolved on new ISIN if records agree | EQ OK | Owner may ACCEPT membership | Price gate may still fail (OD-PX-2) |
| BAJFINANCE / GRASIM ambiguity | List presence ≠ identity | `AMBIGUOUS` | EQ may exist | Do not force ACCEPT until OD-ID-1/2 | Identity gate fails closed |
| Normal verified symbol change | SUFFICIENT via `symbolchange.csv` | Single-ISIN VERIFIED chain | EQ OK | ACCEPT_RECOMMENDED | Membership periods can verify; CA/identity/EOD/price still separate |

**Fundamental rule (reaffirmed):** Membership acceptance never implies identity verification or permission to use non-EQ data.

---

## 10. Owner decision register for the 24 evidence-sufficient groups

**Proposal for owner review - not an approval. Do not write `ACCEPTED`. Do not edit `DECISION_LOG.md`.**

Periods column = backlog `periods_verified_if_group_alone` (periods opened/closed by that group alone; 0 alone ≠ unimportant).

| Group | Effective | Kind | Rows | Evidence file (SHA-256 prefix) | Findings | Boundary EQ / identity | Periods if alone | Recommended owner action | Caveat |
|---|---|---|---|---|---|---|---|---|---|
| G-E06 | 2022-09-30 | RELEASE | 12 | `ind_prs01092022.pdf` `16166ac4…` | Hash match; text extracted; rows agree | Boundary EQ ISINs agree | 8 period strings | Decide ACCEPT/REJECT on all 12 | Page numbers not renderer-verified |
| G-R-2022-12-05-LTIM | 2022-12-05 | RENAME | 1 | `symbolchange.csv` `6937337d…` | Verified rename evidence | Same ISIN across rename | LTI close + LTIM open | Decide | - |
| G-E07 | 2023-03-31 | RELEASE | 10 | `ind_prs17022023_1.pdf` `fc55cd89…` | Hash/content agree | OK | 5 | Decide | - |
| G-I-2023-06-15-VBL | 2023-06-15 | ISIN_CHANGE | 1 | `ca_VBL_2016_2025.json` `62d4c1e4…` | CA body + EQ boundary | INE200M01013→01021 | 0 alone | Decide membership | Source is API body (membership evidence, not CA completeness) |
| G-E08 | 2023-07-13 | RELEASE | 2 | `ind_prs04072023.pdf` `dbc48cbd…` | Agree | OK | 2 | Decide | - |
| G-R-2023-08-24-ADANIENSOL | 2023-08-24 | RENAME | 1 | `symbolchange.csv` `6937337d…` | Agree | Same ISIN | 2 | Decide | Later OD-PX-3 is separate |
| G-E10 | 2023-09-07 | RELEASE | 1 | `ind_prs05092023.pdf` `b8b7f563…` | Agree | JIOFIN EQ | 0 alone | Decide | Period needs other rows |
| G-I-2023-09-28-HAL | 2023-09-28 | ISIN_CHANGE | 1 | `ca_HAL_…json` `782706ca…` | Agree | ISIN change | 1 | Decide | API body as membership corroboration |
| G-E11 | 2023-09-29 | RELEASE | 11 | `ind_prs17082023.pdf` `0b9a68a6…` | Agree | OK | 8 | Decide | - |
| G-I-2024-01-05-NESTLEIND | 2024-01-05 | ISIN_CHANGE | 1 | `ca_NESTLEIND_…` `eaf9b5f7…` | Agree | OK | 2 | Decide | - |
| G-E12 | 2024-03-28 | RELEASE | 10 | `ind_prs28022024.pdf` `5c70d043…` | Agree | OK | 8 | Decide | - |
| G-I-2024-05-15-CANBK | 2024-05-15 | ISIN_CHANGE | 1 | `ca_CANBK_…` `69b7f73d…` | Agree | OK | 1 | Decide | - |
| G-R-2024-06-07-UNITDSPR | 2024-06-07 | RENAME | 1 | `symbolchange.csv` | Agree | Same ISIN | 2 | Decide | - |
| G-E13 | 2024-08-30 | RELEASE | 1 | `ind_prs23082024_1.pdf` `2e22a0f1…` | Agree | TATAMTRDVR | 0 alone | Decide | - |
| G-I-2024-09-12-VBL | 2024-09-12 | ISIN_CHANGE | 1 | `ca_VBL_…` | Membership evidence OK; rec=`INSUFFICIENT_EVIDENCE` | INE200M01021→01039 | 1 | Decide membership with OD-PX-2 note | Split ratio unparsed - price gate, not membership |
| G-E14 | 2024-09-30 | RELEASE | 10 | `ind_prs23082024.pdf` `efc8eab5…` | Agree | OK | 7 | Decide | - |
| G-I-2024-10-28-DRREDDY | 2024-10-28 | ISIN_CHANGE | 1 | `ca_DRREDDY_…` | Agree | OK | 2 | Decide | - |
| G-I-2025-01-10-SHRIRAMFIN | 2025-01-10 | ISIN_CHANGE | 1 | `ca_SHRIRAMFIN_…` | Agree | OK | 1 | Decide | - |
| G-E17 | 2025-03-28 | RELEASE | 10 | `ind_prs21022025.pdf` `1b3a52ab…` | Agree | OK | 4 | Decide | - |
| G-R-2025-04-09-ETERNAL | 2025-04-09 | RENAME | 1 | `symbolchange.csv` | Agree | Same ISIN | 2 | Decide | - |
| G-I-2025-05-07-NAUKRI | 2025-05-07 | ISIN_CHANGE | 1 | `ca_NAUKRI_…` | Agree | OK | 2 | Decide | - |
| G-I-2025-09-22-ADANIPOWER | 2025-09-22 | ISIN_CHANGE | 1 | `ca_ADANIPOWER_…` | Agree | OK | 1 | Decide | Prior BE stretches stay EOD-excluded |
| G-E20 | 2025-09-30 | RELEASE | 10 | `ind_prs22082025.pdf` `731113af…` | Agree | Includes ENRIN ADD | 9 | Decide | ENRIN BE history separate |
| G-R-2025-10-24-TMPV | 2025-10-24 | RENAME | 1 | `symbolchange.csv` | Agree | Same ISIN | 2 | Decide | - |

---

## 11. Explanation of the 14 evidence-insufficient groups

| Group | Why unresolved | Missing evidence | Do not force through validator |
|---|---|---|---|
| G-BASELINE-2020-12-31 | List decrypted; no ISINs; BAJFINANCE/GRASIM identity open | Single-effective-date ISIN notices (OD-ID-1/2) | Yes - identity UNKNOWN |
| G-E09 | Dummy ADD DUMMYREL; no bhavcopy/instrument; release may not print DUMMYREL | Non-tradable seat policy (OD-MEM-2/3) if full-index claim needed | Yes |
| G-E15 | DUMMYITC | Same | Yes |
| G-E18 | DUMMYSIEMS | Same | Yes |
| G-E21 | DUMMYTATAM | Same | Yes |
| G-E23 | DUMMYHDLVR | Same | Yes |
| G-R-2023-08-21-JIOFIN | Dummy→JIOFIN; first rows BE | EQ boundary cannot exist for dummy | Membership may later be owner-decided; EQ still fails |
| G-R-2025-01-29-ITCHOTELS | Dummy→ITCHOTELS; BE | Same | Same |
| G-R-2025-06-19-ENRIN | Dummy→ENRIN; BE | Same | Same |
| G-R-2025-11-12-TMCV | Dummy→TMCV; BE | Same | Same |
| G-E16 | REMOVE ITCHOTELS; no EQ boundary | BE-only trading | Inference: membership decidable from release; research still excluded |
| G-E19 | REMOVE ENRIN | Same | Same |
| G-E22 | REMOVE TMCV | Same | Same |
| G-I-2025-06-16-BAJFINANCE | Predecessor ISIN unresolved | OD-ID-1 | Yes |

---

## 12. Historical dataset scope and certification integrity

**Verified distinctions (still separate in builder outputs):**

1. Historical Nifty 100 reference history (`nifty100_universe.csv` / history export)  
2. Certified research universe (`P0_CERTIFIED_RESEARCH_UNIVERSE.csv` - currently empty)  
3. Exclusion register (`P0_RESEARCH_EXCLUSION_REGISTER.csv`)

**Projection 85 → ~175 verified membership periods:** handoff **fact** that it is a dry-run on a scratch copy, not a certified outcome. This audit did not re-run that scratch simulation. Optimising for that number must not weaken gates.

**Fail-closed still in force (code + current summary):**

| Condition | Still fails closed? |
|---|---|
| Unknown / ambiguous identity | Yes (`identity_value` / rename policy) |
| Incomplete CA coverage | Yes (0 proved windows; every member-date fails CA gate) |
| Unverified membership | Yes (100 periods unverified) |
| Missing EQ data | Yes (`NON_EQ_ONLY` / `NO_EQ_ROW`; 260 member-dates) |
| Unresolved price exceptions | Yes (OD-PX-3/4 still exclude) |
| Unparsed CA ratios | Yes (OD-PX-2) |
| Ambiguous rename chains | Yes (`RENAME_AMBIGUOUS`) |

A verified membership period ≠ certified market data. Identity resolution ≠ CA completeness. Price-gate pass ≠ full P0 certification. TradingView parity (TV-1) remains external and separate.

---

## 13. Outstanding external evidence and owner decisions

| ID | Status (fact) | Evidence / decision still required |
|---|---|---|
| **OD-CA-1** | Open, critical path | Independent completeness source(s); collection scope if new downloads; `USER_APPROVED` marker line(s); **owner choice on one- vs two-source bar** |
| **OD-ID-1** | Open | Single-session BAJFINANCE ISIN change record |
| **OD-ID-2** | Open | Single-session GRASIM ISIN change record |
| **B11-P** | Open; D59 holds window at 2020-12-31 | Pre-2020 constituent lists with symbols/ISINs |
| **TV-1** | Waiting | TradingView exports per worksheet; not internal P0 certification |
| **OD-PX-2** | Open | Representable terms (CGPOWER, VBL) |
| **OD-PX-3** | Investigated; optional | Exception rule for reviewed market move |
| **OD-PX-4** | Measured; optional | Rule for steps across held excluded sessions |
| **OD-MEM-2/3** | Open; optional | Dummy seats in a full-index claim |
| **T-001 batch 3+** | Owner | Decisions on the 24 sufficient groups |
| **R-5** | Unresolved | Delivery-council vs Rulebook precedence wording - leave untouched |
| **R-12 residual** | Implemented with limitations | Closes only with real CA completeness |

Do not invent evidence. Do not resolve by inference.

---

## 14. Specialist review findings

### 14.1 P0 data-certification specialist

| Finding | Severity | Evidence | Blocks M2? |
|---|---|---|---|
| Completeness register is single-source; dual-source reconciliation absent | CRITICAL | `COMPLETENESS_COLUMNS`; `load_completeness`; handoff §C recommendation | **Yes** |
| Empty register correctly certifies nothing today | - | `completeness_register.present=false` | No (safe current state) |
| API-as-proof and decision-marker hardening are sound | - | ED-55; tests pass | No |
| Backlog 24/14/25 reconcile; ACCEPT+INSUFFICIENT rows conflate axes | MEDIUM | CSV recompute | Process fix before owner packs |
| ISIN-change groups cite `ca_*.json` as membership evidence | LOW | Backlog `source_file` | OK for membership corroboration; must never be completeness proof |

**Remediation:** Enforce dual-source completeness (or owner-narrow OD-CA-1); split backlog fields; keep agents off ledger `ACCEPTED`.

### 14.2 Quantitative-validation specialist

| Finding | Severity | Evidence | Blocks M2? |
|---|---|---|---|
| Quoting any historical performance from exploratory or uncertified rows remains forbidden | HIGH | D62; `research_use`; 0 certified | Yes for any performance claim |
| Expanding verified periods without CA completeness enlarges *reference* history only | MEDIUM | Dry-run ~175 periods; CA gate still fails all dates | Does not alone block engineering, blocks research claims |
| R-12 residual (26/125 events under 15%) means single incomplete CA source under-certifies risk | CRITICAL | Handoff §G; blockers R-12 | Strengthens OD-CA-1 dual-source need |
| Survivorship / point-in-time: today's constituents not used | - | Universe periods; D59 window | OK |

**Remediation:** No backtest metrics until certified subset exists; treat ~175 as coverage of membership verification only.

### 14.3 Production-readiness specialist

| Finding | Severity | Evidence | Blocks M2? |
|---|---|---|---|
| Certification fingerprint includes code, decision log, CA raw digest | - | `inputs_sha256` | Good |
| Gate can certify without dual independent evidence → false certification risk | CRITICAL | §5 | **Yes** |
| Dirty uncommitted Milestone 1 tree; rebuild overwrite risk | MEDIUM | git status; handoff "no commit" | Operational - isolate M2 writes |
| Blockers doc count drift vs summary | LOW | 73,368 vs 73,366 | Fix docs when next editing |
| `authorises_order` remains false | - | summary reconciliation | OK |

**Remediation:** Close CA loophole before writing any real `completeness.csv`; do not overwrite certification outputs until gate contract matches owner bar; keep TradingView out of P0 pass/fail.

### 14.4 Lead reconciliation

| Topic | Agreement |
|---|---|
| Single-source loophole | All three: CRITICAL; blocks Milestone 2 certification work |
| Membership backlog arithmetic | P0 + lead: PASS reconcile; quant: no performance implication |
| Whether M2 membership *owner packaging* may proceed in parallel | Lead: packaging/docs may be prepared; **writing ACCEPTED / completeness rows / rebuild claiming certification** must wait on OD-CA-1 bar + gate fix |
| One- vs two-source bar | Specialists cannot approve; **owner decision required** (Finding G1) |

No specialist approved an owner-reserved decision.

---

## 15. Required corrections before Milestone 2 implementation

Ordered by severity:

1. **CRITICAL - Close single-source completeness loophole** (or owner-narrow OD-CA-1 in `DECISION_LOG.md`). Minimum engineering if dual-source required: schema for two sources, reconciliation, conflict fail-closed, dual hashes in acceptance marker, regression tests for §6 pass-risk rows.  
2. **HIGH - Do not create `completeness.csv` rows** until (1) is done.  
3. **MEDIUM - Split backlog status fields** (§9) before presenting batch 3+ cards, so ACCEPT_RECOMMENDED cannot be read as identity/EQ clearance.  
4. **MEDIUM - Align blockers doc** exploratory/tier/build_version with `P0_CERTIFICATION_SUMMARY.json`.  
5. **LOW - Clarify in handoff** that ~175 periods is dry-run only (already stated; keep visible on every owner pack).  
6. **Process - Owner decision** on OD-CA-1 acceptance bar (one independent source vs two reconciled sources).

---

## 16. Recommended Milestone 2 execution sequence

1. Owner decides OD-CA-1 evidence bar (dual-source vs explicit single-source).  
2. If dual-source: implement gate + tests; only then approve collection scope for second sources.  
3. Collect / reconcile completeness for currently verified periods first (85), fail closed on conflicts.  
4. Present T-001 batch 3+ with split membership/identity/EQ fields; owner writes `ACCEPTED` only on sufficient groups.  
5. Rebuild certification; expect certified count still 0 until completeness windows exist.  
6. Keep OD-ID-1/2, B11-P, TV-1, OD-PX-* on separate tracks; never weaken gates to grow certified counts.  
7. Final certification report only after gates match the owner bar and reconciliations hold.

**Do not begin steps 2-5 of "certify with current register" until step 1-2 close the loophole.**

---

## 17. Explicit limitations and unresolved questions

- This audit did **not** re-run full `p0_certification.build()` on production data (would rewrite outputs). Counts taken from committed/on-disk `P0_CERTIFICATION_SUMMARY.json` and direct CSV/ledger reads.  
- Dual-source dry-run of a real BSE/NSDL extract was not possible (no acquisition; read-only).  
- Page-level PDF verification still lacks a renderer (handoff limitation retained).  
- Whether the owner intends dual-source OD-CA-1 is **unresolved** (G1).  
- Cumulative ~175 period projection not re-simulated.  
- R-5 remains unresolved by instruction.  
- Exploratory label string in summary is `EXPLORATORY_ONLY_NOT_CERTIFIED` (73,366); some docs say "exploratory only" without the suffix.

---

## 18. Final certification-readiness assessment

| Question | Answer |
|---|---|
| Is P0 complete? | **No** |
| Are any historical member-dates certified? | **No (0)** |
| Is the Milestone 2 handoff arithmetically sound on membership? | **Yes (24/14/25; ledger 140/131; 85/185)** |
| Is the CA completeness *mechanism* safe against the intended independent-evidence standard? | **No** |
| Preflight status | **`PREFLIGHT_BLOCKED`** |
| Authorises trading / orders? | **No** (`authorises_order` false; research system only) |

A passing preflight would not have certified data. This blocked preflight means Milestone 2 must not implement certification closure on the current one-source register without an explicit owner narrowing of OD-CA-1.

---

## Finding index (severity)

| ID | Severity | Summary |
|---|---|---|
| A-SINGLE-SOURCE | CRITICAL | One approved non-API file + marker → CA verified / covered-none |
| A-NO-RECONCILE | CRITICAL | No event-by-event dual-source reconciliation |
| G1-BAR-AMBIGUITY | MEDIUM | D62 tiers vs handoff dual-source recommendation; owner must choose |
| B-FIELD-CONFLATION | MEDIUM | 9× ACCEPT_RECOMMENDED + EVIDENCE_INSUFFICIENT |
| B-VBL-REC | LOW | VBL membership sufficient vs recommendation insufficient (OD-PX-2) |
| C-DOC-DRIFT | LOW | Blockers 73,368 / 108,325 / build 1.1.0 vs summary 73,366 / 108,323 / 1.5.0 |
| OPS-DIRTY-TREE | MEDIUM | Large uncommitted M1 tree; protect against overwrite |

---

*End of preflight audit. Hand findings to the project owner. Do not begin Milestone 2 implementation from this document alone.*
