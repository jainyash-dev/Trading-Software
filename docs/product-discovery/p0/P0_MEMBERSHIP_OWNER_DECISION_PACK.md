# P0 Batch 4 - Membership owner decision pack

**Date:** 2026-11-15  
**Authority:** Agents must not write `ACCEPTED`/`REJECTED` (D49/D53/ED-27/ED-35/ED-48).  
**Ledger:** `nse/data/universe/nifty100_review.csv` (140 ACCEPTED, 131 blank).  
**Four fields kept independent:** membership_evidence_status, identity_evidence_status, eq_data_status, owner_membership_recommendation.

Named focus symbols reviewed in backlog: BAJFINANCE, GRASIM, JIOFIN, ITCHOTELS, ENRIN, TMCV, VBL, plus dummy-to-listed and BE/BZ-only periods.

## A. Evidence-sufficient groups (owner decision required)

Group count: **24**

### G-E06

- Effective date: `2022-09-30`
- Kind: `RELEASE`
- Symbols: ATGL, BEL, HAL, IRCTC, JUBLFOOD, LUPIN, MINDTREE, MOTHERSON, MPHASIS, PNB, SAIL, ZYDUSLIFE
- Rows: 12
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs01092022.pdf`
- Source SHA-256: `16166ac483166d47c9b0aef2293f86e0c82a619999bd71902ee97803de89a0e1`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: BEL INE263A01024 2022-09-30..open; JUBLFOOD INE797F01020 2022-04-20..2022-09-29; LUPIN INE326A01037 2020-12-31..2022-09-29; MINDTREE INE018I01017 2022-03-31..2022-09-29; MOTHERSON INE775A01035 2022-09-30..open; PNB INE160A01022 2020-12-31..2022-09-29; SAIL INE114A01011 2021-09-30..2022-09-29; ZYDUSLIFE INE010B01027 2022-03-07..2022-09-29
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E06:REMOVE:JUBLFOOD:INE797F01020`
  - `change:E06:REMOVE:LUPIN:INE326A01037`
  - `change:E06:REMOVE:MINDTREE:INE018I01017`
  - `change:E06:REMOVE:PNB:INE160A01022`
  - `change:E06:REMOVE:SAIL:INE114A01011`
  - `change:E06:REMOVE:ZYDUSLIFE:INE010B01027`
  - `change:E06:ADD:ATGL:INE399L01023`
  - `change:E06:ADD:BEL:INE263A01024`
  - `change:E06:ADD:HAL:INE066F01012`
  - `change:E06:ADD:IRCTC:INE335Y01020`
  - `change:E06:ADD:MPHASIS:INE356A01018`
  - `change:E06:ADD:MOTHERSON:INE775A01035`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E07

- Effective date: `2023-03-31`
- Kind: `RELEASE`
- Symbols: ABB, AWL, BANDHANBNK, BIOCON, CANBK, GLAND, MPHASIS, PAGEIND, PAYTM, VBL
- Rows: 10
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs17022023_1.pdf`
- Source SHA-256: `fc55cd8916629df82b94a31e03c050b096bcbf98bcd1fb6e700c3223e93b8cbe`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: ABB INE117A01022 2023-03-31..open; BANDHANBNK INE545U01014 2020-12-31..2023-03-30; BIOCON INE376G01013 2020-12-31..2023-03-30; GLAND INE068V01023 2021-06-30..2023-03-30; PAYTM INE982J01020 2022-03-31..2023-03-30
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E07:REMOVE:BANDHANBNK:INE545U01014`
  - `change:E07:REMOVE:BIOCON:INE376G01013`
  - `change:E07:REMOVE:GLAND:INE068V01023`
  - `change:E07:REMOVE:MPHASIS:INE356A01018`
  - `change:E07:REMOVE:PAYTM:INE982J01020`
  - `change:E07:ADD:ABB:INE117A01022`
  - `change:E07:ADD:AWL:INE699H01024`
  - `change:E07:ADD:CANBK:INE476A01014`
  - `change:E07:ADD:PAGEIND:INE761H01022`
  - `change:E07:ADD:VBL:INE200M01013`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E08

- Effective date: `2023-07-13`
- Kind: `RELEASE`
- Symbols: HDFC, JINDALSTEL
- Rows: 2
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs04072023.pdf`
- Source SHA-256: `dbc48cbd8b127ca35df4fbac956964dc0922d282baab25956025beb20ba65cb0`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: HDFC INE001A01036 2020-12-31..2023-07-12; JINDALSTEL INE749A01030 2023-07-13..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E08:REMOVE:HDFC:INE001A01036`
  - `change:E08:ADD:JINDALSTEL:INE749A01030`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E10

- Effective date: `2023-09-07`
- Kind: `RELEASE`
- Symbols: JIOFIN
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs05092023.pdf`
- Source SHA-256: `b8b7f5638efcc5e40c7dd04856b5aac5ec82fa8f43c7a6f285f6f3bd2aeae3f4`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E10:REMOVE:JIOFIN:INE758E01017`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E11

- Effective date: `2023-09-29`
- Kind: `RELEASE`
- Symbols: ACC, HDFCAMC, INDUSTOWER, NYKAA, PAGEIND, PNB, SHRIRAMFIN, TATAMTRDVR, TRENT, TVSMOTOR, ZYDUSLIFE
- Rows: 11
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs17082023.pdf`
- Source SHA-256: `0b9a68a6144c07a2d2063a066c7dc20a767736740b7204e72d66ddeee3936daf`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: ACC INE012A01025 2020-12-31..2023-09-28; HDFCAMC INE127D01025 2020-12-31..2023-09-28; INDUSTOWER INE121J01017 2020-12-31..2023-09-28; NYKAA INE388Y01029 2022-03-31..2023-09-28; PNB INE160A01022 2023-09-29..open; TRENT INE849A01020 2023-09-29..open; TVSMOTOR INE494B01023 2023-09-29..open; ZYDUSLIFE INE010B01027 2023-09-29..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E11:REMOVE:ACC:INE012A01025`
  - `change:E11:REMOVE:NYKAA:INE388Y01029`
  - `change:E11:REMOVE:HDFCAMC:INE127D01025`
  - `change:E11:REMOVE:INDUSTOWER:INE121J01017`
  - `change:E11:REMOVE:PAGEIND:INE761H01022`
  - `change:E11:ADD:PNB:INE160A01022`
  - `change:E11:ADD:SHRIRAMFIN:INE721A01013`
  - `change:E11:ADD:TRENT:INE849A01020`
  - `change:E11:ADD:TVSMOTOR:INE494B01023`
  - `change:E11:ADD:ZYDUSLIFE:INE010B01027`
  - `change:E11:ADD:TATAMTRDVR:IN9155A01020`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E12

- Effective date: `2024-03-28`
- Kind: `RELEASE`
- Symbols: ADANIPOWER, AWL, IRFC, JIOFIN, MUTHOOTFIN, PFC, PGHH, PIIND, RECLTD, UPL
- Rows: 10
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs28022024.pdf`
- Source SHA-256: `5c70d043edde682a31fc5fa043a3b829a380fc9896de904bcb76d64b8319f698`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: IRFC INE053F01010 2024-03-28..open; JIOFIN INE758E01017 2024-03-28..open; MUTHOOTFIN INE414G01012 2020-12-31..2024-03-27; PFC INE134E01011 2024-03-28..open; PGHH INE179A01014 2020-12-31..2024-03-27; PIIND INE603J01030 2021-09-30..2024-03-27; RECLTD INE020B01018 2024-03-28..open; UPL INE628A01036 2020-12-31..2024-03-27
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E12:REMOVE:AWL:INE699H01024`
  - `change:E12:REMOVE:MUTHOOTFIN:INE414G01012`
  - `change:E12:REMOVE:PIIND:INE603J01030`
  - `change:E12:REMOVE:PGHH:INE179A01014`
  - `change:E12:REMOVE:UPL:INE628A01036`
  - `change:E12:ADD:ADANIPOWER:INE814H01011`
  - `change:E12:ADD:IRFC:INE053F01010`
  - `change:E12:ADD:JIOFIN:INE758E01017`
  - `change:E12:ADD:PFC:INE134E01011`
  - `change:E12:ADD:RECLTD:INE020B01018`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E13

- Effective date: `2024-08-30`
- Kind: `RELEASE`
- Symbols: TATAMTRDVR
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs23082024_1.pdf`
- Source SHA-256: `2e22a0f1e9b39633aa2551553c8592eb67d9b8488e09ceab71e60d3025eee7f8`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E13:REMOVE:TATAMTRDVR:IN9155A01020`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E14

- Effective date: `2024-09-30`
- Kind: `RELEASE`
- Symbols: BERGEPAINT, BHEL, COLPAL, JSWENERGY, LODHA, MARICO, NHPC, SBICARD, SRF, UNIONBANK
- Rows: 10
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs23082024.pdf`
- Source SHA-256: `efc8eab5d129eaa2219e10b57ab9a5c3ce2d0cd7b8c5ebd2c7b6bc244a38b2b8`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: BERGEPAINT INE463A01038 2020-12-31..2024-09-29; COLPAL INE259A01022 2020-12-31..2024-09-29; JSWENERGY INE121E01018 2024-09-30..open; LODHA INE670K01029 2024-09-30..open; MARICO INE196A01026 2020-12-31..2024-09-29; SBICARD INE018E01016 2020-12-31..2024-09-29; SRF INE647A01010 2022-03-31..2024-09-29
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E14:REMOVE:BERGEPAINT:INE463A01038`
  - `change:E14:REMOVE:COLPAL:INE259A01022`
  - `change:E14:REMOVE:MARICO:INE196A01026`
  - `change:E14:REMOVE:SBICARD:INE018E01016`
  - `change:E14:REMOVE:SRF:INE647A01010`
  - `change:E14:ADD:BHEL:INE257A01026`
  - `change:E14:ADD:JSWENERGY:INE121E01018`
  - `change:E14:ADD:LODHA:INE670K01029`
  - `change:E14:ADD:NHPC:INE848E01016`
  - `change:E14:ADD:UNIONBANK:INE692A01016`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E17

- Effective date: `2025-03-28`
- Kind: `RELEASE`
- Symbols: ATGL, BAJAJHFL, BHEL, CGPOWER, HYUNDAI, INDHOTEL, IRCTC, NHPC, SWIGGY, UNIONBANK
- Rows: 10
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs21022025.pdf`
- Source SHA-256: `1b3a52abf5954f4b213f5b555ee8776ff596f0adde0612cfdd5409b109195370`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: BAJAJHFL INE377Y01014 2025-03-28..open; CGPOWER INE067A01029 2025-03-28..open; HYUNDAI INE0V6F01027 2025-03-28..open; INDHOTEL INE053A01029 2025-03-28..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E17:REMOVE:ATGL:INE399L01023`
  - `change:E17:REMOVE:BHEL:INE257A01026`
  - `change:E17:REMOVE:IRCTC:INE335Y01020`
  - `change:E17:REMOVE:NHPC:INE848E01016`
  - `change:E17:REMOVE:UNIONBANK:INE692A01016`
  - `change:E17:ADD:BAJAJHFL:INE377Y01014`
  - `change:E17:ADD:CGPOWER:INE067A01029`
  - `change:E17:ADD:HYUNDAI:INE0V6F01027`
  - `change:E17:ADD:INDHOTEL:INE053A01029`
  - `change:E17:ADD:SWIGGY:INE00H001014`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E20

- Effective date: `2025-09-30`
- Kind: `RELEASE`
- Symbols: DABUR, ENRIN, HEROMOTOCO, HINDZINC, ICICIPRULI, INDUSINDBK, MAXHEALTH, MAZDOCK, SOLARINDS, SWIGGY
- Rows: 10
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs22082025.pdf`
- Source SHA-256: `731113af85aad6b54cce359d5465d84e6062b28b03c21cd9922a20a3f44d2de1`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: DABUR INE016A01026 2020-12-31..2025-09-29; ENRIN INE1NPP01017 2025-09-30..open; HEROMOTOCO INE158A01026 2020-12-31..2025-09-29; HINDZINC INE267A01025 2025-09-30..open; ICICIPRULI INE726G01019 2020-12-31..2025-09-29; INDUSINDBK INE095A01012 2020-12-31..2025-09-29; MAXHEALTH INE027H01010 2025-09-30..open; MAZDOCK INE249Z01020 2025-09-30..open; SOLARINDS INE343H01029 2025-09-30..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E20:REMOVE:DABUR:INE016A01026`
  - `change:E20:REMOVE:HEROMOTOCO:INE158A01026`
  - `change:E20:REMOVE:ICICIPRULI:INE726G01019`
  - `change:E20:REMOVE:INDUSINDBK:INE095A01012`
  - `change:E20:REMOVE:SWIGGY:INE00H001014`
  - `change:E20:ADD:HINDZINC:INE267A01025`
  - `change:E20:ADD:MAXHEALTH:INE027H01010`
  - `change:E20:ADD:MAZDOCK:INE249Z01020`
  - `change:E20:ADD:ENRIN:INE1NPP01017`
  - `change:E20:ADD:SOLARINDS:INE343H01029`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2023-06-15-VBL

- Effective date: `2023-06-15`
- Kind: `ISIN_CHANGE`
- Symbols: VBL
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_VBL_2016_2025.json`
- Source SHA-256: `62d4c1e43aec38898500748591ea03310bad29cec0876b8fa2abc655d2cfb423`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2023-06-15-VBL:ISIN_CHANGE:VBL:INE200M01021`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2023-09-28-HAL

- Effective date: `2023-09-28`
- Kind: `ISIN_CHANGE`
- Symbols: HAL
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_HAL_2016_2025.json`
- Source SHA-256: `782706cab0f342d680c0d0f734de53f474b2da59b6f42772152402a6fb13966b`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: HAL INE066F01020 2023-09-28..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2023-09-28-HAL:ISIN_CHANGE:HAL:INE066F01020`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2024-01-05-NESTLEIND

- Effective date: `2024-01-05`
- Kind: `ISIN_CHANGE`
- Symbols: NESTLEIND
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_NESTLEIND_2016_2025.json`
- Source SHA-256: `eaf9b5f752e38f8b237a6f969c2b3518ee20e172f1b5a23ee513469e843554ec`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: NESTLEIND INE239A01016 2020-12-31..2024-01-04; NESTLEIND INE239A01024 2024-01-05..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2024-01-05-NESTLEIND:ISIN_CHANGE:NESTLEIND:INE239A01024`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2024-05-15-CANBK

- Effective date: `2024-05-15`
- Kind: `ISIN_CHANGE`
- Symbols: CANBK
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_CANBK_2016_2025.json`
- Source SHA-256: `69b7f73d631fde3fcfbc13a817a8e6d24eaf475710d0fc572bae56119d88951a`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: CANBK INE476A01022 2024-05-15..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2024-05-15-CANBK:ISIN_CHANGE:CANBK:INE476A01022`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2024-09-12-VBL

- Effective date: `2024-09-12`
- Kind: `ISIN_CHANGE`
- Symbols: VBL
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_VBL_2016_2025.json`
- Source SHA-256: `62d4c1e43aec38898500748591ea03310bad29cec0876b8fa2abc655d2cfb423`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: VBL INE200M01039 2024-09-12..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2024-09-12-VBL:ISIN_CHANGE:VBL:INE200M01039`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2024-10-28-DRREDDY

- Effective date: `2024-10-28`
- Kind: `ISIN_CHANGE`
- Symbols: DRREDDY
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_DRREDDY_2016_2025.json`
- Source SHA-256: `c3193c43b228101aafdca2518d44235dda40dba7024bea1e1e989de080134f23`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: DRREDDY INE089A01023 2020-12-31..2024-10-27; DRREDDY INE089A01031 2024-10-28..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2024-10-28-DRREDDY:ISIN_CHANGE:DRREDDY:INE089A01031`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2025-01-10-SHRIRAMFIN

- Effective date: `2025-01-10`
- Kind: `ISIN_CHANGE`
- Symbols: SHRIRAMFIN
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_SHRIRAMFIN_2016_2025.json`
- Source SHA-256: `b32f29ec37730d7e3020a27f25426efcf41cdde1648c5420333a60d265fc06f2`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: SHRIRAMFIN INE721A01047 2025-01-10..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2025-01-10-SHRIRAMFIN:ISIN_CHANGE:SHRIRAMFIN:INE721A01047`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2025-05-07-NAUKRI

- Effective date: `2025-05-07`
- Kind: `ISIN_CHANGE`
- Symbols: NAUKRI
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_NAUKRI_2016_2025.json`
- Source SHA-256: `38f643e8a5618ce7a4a84895280837e7c6ec72e7745a79bf07b8d23ed529c964`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: NAUKRI INE663F01024 2020-12-31..2025-05-06; NAUKRI INE663F01032 2025-05-07..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2025-05-07-NAUKRI:ISIN_CHANGE:NAUKRI:INE663F01032`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2025-09-22-ADANIPOWER

- Effective date: `2025-09-22`
- Kind: `ISIN_CHANGE`
- Symbols: ADANIPOWER
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_ADANIPOWER_2016_2025.json`
- Source SHA-256: `88b21aa668309ebe543cf503548907238df1a35274bb032e864415e02cc858b7`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: ADANIPOWER INE814H01029 2025-09-22..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2025-09-22-ADANIPOWER:ISIN_CHANGE:ADANIPOWER:INE814H01029`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2022-12-05-LTIM

- Effective date: `2022-12-05`
- Kind: `RENAME`
- Symbols: LTIM
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/identity/symbolchange.csv`
- Source SHA-256: `6937337dd726222cd6bb5c8af9964073d215a84f28e7edecf1861f25fd3fd66f`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: LTI INE214T01019 2020-12-31..2022-12-04; LTIM INE214T01019 2022-12-05..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2022-12-05-LTIM:RENAME:LTIM:INE214T01019`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2023-08-24-ADANIENSOL

- Effective date: `2023-08-24`
- Kind: `RENAME`
- Symbols: ADANIENSOL
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/identity/symbolchange.csv`
- Source SHA-256: `6937337dd726222cd6bb5c8af9964073d215a84f28e7edecf1861f25fd3fd66f`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: ADANIENSOL INE931S01010 2023-08-24..open; ADANITRANS INE931S01010 2020-12-31..2023-08-23
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2023-08-24-ADANIENSOL:RENAME:ADANIENSOL:INE931S01010`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2024-06-07-UNITDSPR

- Effective date: `2024-06-07`
- Kind: `RENAME`
- Symbols: UNITDSPR
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/identity/symbolchange.csv`
- Source SHA-256: `6937337dd726222cd6bb5c8af9964073d215a84f28e7edecf1861f25fd3fd66f`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: MCDOWELL-N INE854D01024 2020-12-31..2024-06-06; UNITDSPR INE854D01024 2024-06-07..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2024-06-07-UNITDSPR:RENAME:UNITDSPR:INE854D01024`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2025-04-09-ETERNAL

- Effective date: `2025-04-09`
- Kind: `RENAME`
- Symbols: ETERNAL
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/identity/symbolchange.csv`
- Source SHA-256: `6937337dd726222cd6bb5c8af9964073d215a84f28e7edecf1861f25fd3fd66f`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: ETERNAL INE758T01015 2025-04-09..open; ZOMATO INE758T01015 2022-03-31..2025-04-08
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2025-04-09-ETERNAL:RENAME:ETERNAL:INE758T01015`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2025-10-24-TMPV

- Effective date: `2025-10-24`
- Kind: `RENAME`
- Symbols: TMPV
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `RESOLVED_VERIFIED`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/identity/symbolchange.csv`
- Source SHA-256: `6937337dd726222cd6bb5c8af9964073d215a84f28e7edecf1861f25fd3fd66f`
- Hash matches: `True`
- Missing evidence: (none listed)
- Periods verified if group alone: TATAMOTORS INE155A01022 2020-12-31..2025-10-23; TMPV INE155A01022 2025-10-24..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2025-10-24-TMPV:RENAME:TMPV:INE155A01022`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

## B. Evidence-insufficient groups

Group count: **14**

### G-BASELINE-2020-12-31

- Effective date: `2020-12-31`
- Kind: `BASELINE`
- Symbols: BAJFINANCE, GRASIM
- Rows: 2
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `AMBIGUOUS`
- eq_data_status: `EQ_BOUNDARY_OK`
- owner_membership_recommendation: `DEFER` (recommendation only)
- Source: `nse/data/universe/evidence/baseline/indices_dataDec2020.zip`
- Source SHA-256: `61922f25601735aeb00d534f04de99924607cc4f51ad1cc8777f61720af3ba0c`
- Hash matches: `True`
- Missing evidence: GRASIM: an official record joining ISIN INE047A01013 to INE047A01021 with one effective date (held MSEI circular msei_grasim_4581_2016.pdf states two dates per README; instrument records keep two open LISTING records, so resolve() is UNKNOWN_INSTRUMENT on every date) | BAJFINANCE: an official record joining ISIN INE296A01016 to INE296A01024 with one effective date (held MSEI circular msei_bajfinance_4496_2016.pdf states two dates per README); until then resolve() is UNKNOWN_INSTRUMENT before 2025-06-16 | The constituent list prints no ISIN: the ISIN is taken from the 2021-01-01 bhavcopy | baseline:BAJFINANCE:INE296A01024: identity on 2020-12-31 is UNKNOWN_INSTRUMENT (two or more ISINs are listed as BAJFINANCE on 2020-12-31: INE296A01016, INE296A01024) | baseline:GRASIM:INE047A01021: identity on 2020-12-31 is UNKNOWN_INSTRUMENT (two or more ISINs are listed as GRASIM on 2020-12-31: INE047A01013, INE047A01021)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `baseline:BAJFINANCE:INE296A01024`
  - `baseline:GRASIM:INE047A01021`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E09

- Effective date: `2023-07-20`
- Kind: `RELEASE`
- Symbols: DUMMYREL
- Rows: 1
- membership_evidence_status: `INSUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NO_ROW`
- owner_membership_recommendation: `DEFER` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs17072023.pdf`
- Source SHA-256: `dc666369d2d960fc7045f0e5b44e8f606e33b97617b962444ab3e500e7c80702`
- Hash matches: `True`
- Missing evidence: change:E09:ADD:DUMMYREL:INE758E01017: no EQ row with ISIN INE758E01017 for DUMMYREL on the after boundary 2023-07-20 (no row for DUMMYREL in this file (any series)) | change:E09:ADD:DUMMYREL:INE758E01017: identity for DUMMYREL on 2023-07-20 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYREL) | release does not print symbol DUMMYREL; the symbol rests on another document | DUMMYREL: placeholder symbol with no bhavcopy row and no instrument record; ISIN is an inference from a later document
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E09:ADD:DUMMYREL:INE758E01017`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E15

- Effective date: `2025-01-06`
- Kind: `RELEASE`
- Symbols: DUMMYITC
- Rows: 1
- membership_evidence_status: `INSUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NO_ROW`
- owner_membership_recommendation: `DEFER` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs30122024.pdf`
- Source SHA-256: `ed408284ea6d56b1e21bf1c0a20166b56546440587670b21f56cf57439322229`
- Hash matches: `True`
- Missing evidence: change:E15:ADD:DUMMYITC:INE379A01028: no EQ row with ISIN INE379A01028 for DUMMYITC on the after boundary 2025-01-06 (no row for DUMMYITC in this file (any series)) | change:E15:ADD:DUMMYITC:INE379A01028: identity for DUMMYITC on 2025-01-06 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYITC) | DUMMYITC: placeholder symbol with no bhavcopy row and no instrument record; ISIN is an inference from a later document
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E15:ADD:DUMMYITC:INE379A01028`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E16

- Effective date: `2025-02-10`
- Kind: `RELEASE`
- Symbols: ITCHOTELS
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NON_EQ_ONLY`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs06022025_1.pdf`
- Source SHA-256: `60f61a6f41b2aa2f9f769d8fc42c4c090f03ae84b44af62827ea46ccd4d88878`
- Hash matches: `True`
- Missing evidence: change:E16:REMOVE:ITCHOTELS:INE379A01028: no EQ row with ISIN INE379A01028 for ITCHOTELS on the before boundary 2025-02-07 (NO EQ ROW; only series BE) [a BE row with the ledger ISIN exists]
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E16:REMOVE:ITCHOTELS:INE379A01028`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E18

- Effective date: `2025-04-07`
- Kind: `RELEASE`
- Symbols: DUMMYSIEMS
- Rows: 1
- membership_evidence_status: `INSUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NO_ROW`
- owner_membership_recommendation: `DEFER` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs02042025.pdf`
- Source SHA-256: `4c3f4315e94ddb8919bb947bd06c858244256f66e39e264b655b0a08f78ab99b`
- Hash matches: `True`
- Missing evidence: change:E18:ADD:DUMMYSIEMS:INE1NPP01017: no EQ row with ISIN INE1NPP01017 for DUMMYSIEMS on the after boundary 2025-04-07 (no row for DUMMYSIEMS in this file (any series)) | change:E18:ADD:DUMMYSIEMS:INE1NPP01017: identity for DUMMYSIEMS on 2025-04-07 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYSIEMS) | DUMMYSIEMS: placeholder symbol with no bhavcopy row and no instrument record; ISIN is an inference from a later document
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E18:ADD:DUMMYSIEMS:INE1NPP01017`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E19

- Effective date: `2025-06-27`
- Kind: `RELEASE`
- Symbols: ENRIN
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NON_EQ_ONLY`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs25062025_2.pdf`
- Source SHA-256: `dd21c18f5dfcc014cd045c6a574097a8d5cf3f0ef076005bc67f18bab65c883f`
- Hash matches: `True`
- Missing evidence: change:E19:REMOVE:ENRIN:INE1NPP01017: no EQ row with ISIN INE1NPP01017 for ENRIN on the before boundary 2025-06-26 (NO EQ ROW; only series BE) [a BE row with the ledger ISIN exists]
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E19:REMOVE:ENRIN:INE1NPP01017`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E21

- Effective date: `2025-10-14`
- Kind: `RELEASE`
- Symbols: DUMMYTATAM
- Rows: 1
- membership_evidence_status: `INSUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NO_ROW`
- owner_membership_recommendation: `DEFER` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs07102025.pdf`
- Source SHA-256: `58bafe38fcb153c8ee2794589497b452484b53f3a8c77247d7434368967b2459`
- Hash matches: `True`
- Missing evidence: change:E21:ADD:DUMMYTATAM:INE1TAE01010: no EQ row with ISIN INE1TAE01010 for DUMMYTATAM on the after boundary 2025-10-14 (no row for DUMMYTATAM in this file (any series)) | change:E21:ADD:DUMMYTATAM:INE1TAE01010: identity for DUMMYTATAM on 2025-10-14 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYTATAM) | DUMMYTATAM: placeholder symbol with no bhavcopy row and no instrument record; ISIN is an inference from a later document
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E21:ADD:DUMMYTATAM:INE1TAE01010`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E22

- Effective date: `2025-11-17`
- Kind: `RELEASE`
- Symbols: TMCV
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NON_EQ_ONLY`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs13112025.pdf`
- Source SHA-256: `57dd346835e402f5f5384672f7f7beb71ddf4d67e1af604251fa2ce27b286ea4`
- Hash matches: `True`
- Missing evidence: change:E22:REMOVE:TMCV:INE1TAE01010: no EQ row with ISIN INE1TAE01010 for TMCV on the before boundary 2025-11-14 (NO EQ ROW; only series BE) [a BE row with the ledger ISIN exists]
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E22:REMOVE:TMCV:INE1TAE01010`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-E23

- Effective date: `2025-12-05`
- Kind: `RELEASE`
- Symbols: DUMMYHDLVR
- Rows: 1
- membership_evidence_status: `INSUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NO_ROW`
- owner_membership_recommendation: `DEFER` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs28112025.pdf`
- Source SHA-256: `078792ab1f1b61cdcb62c19c8f144143be3c7e7a5fc5ebe5f6834dbee9954200`
- Hash matches: `True`
- Missing evidence: change:E23:ADD:DUMMYHDLVR:INE2KCE01013: no EQ row with ISIN INE2KCE01013 for DUMMYHDLVR on the after boundary 2025-12-05 (no row for DUMMYHDLVR in this file (any series)) | change:E23:ADD:DUMMYHDLVR:INE2KCE01013: identity for DUMMYHDLVR on 2025-12-05 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYHDLVR) | DUMMYHDLVR: placeholder symbol with no bhavcopy row and no instrument record; ISIN is an inference from a later document
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:E23:ADD:DUMMYHDLVR:INE2KCE01013`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-I-2025-06-16-BAJFINANCE

- Effective date: `2025-06-16`
- Kind: `ISIN_CHANGE`
- Symbols: BAJFINANCE
- Rows: 1
- membership_evidence_status: `INSUFFICIENT`
- identity_evidence_status: `AMBIGUOUS`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `DEFER` (recommendation only)
- Source: `nse/data/corporate_actions/raw/ca_BAJFINANCE_2016_2025.json`
- Source SHA-256: `fa813f2c4be5198ed04e2e886d30035b0983fad11b2436051d4e4fa60806817b`
- Hash matches: `True`
- Missing evidence: change:I-2025-06-16-BAJFINANCE:ISIN_CHANGE:BAJFINANCE:INE296A01032: identity for BAJFINANCE on 2025-06-13 is UNKNOWN_INSTRUMENT isin=None verified=False (two or more ISINs are listed as BAJFINANCE on 2025-06-13: INE296A01016, INE296A01024)
- Periods verified if group alone: BAJFINANCE INE296A01032 2025-06-16..open
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:I-2025-06-16-BAJFINANCE:ISIN_CHANGE:BAJFINANCE:INE296A01032`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2023-08-21-JIOFIN

- Effective date: `2023-08-21`
- Kind: `RENAME`
- Symbols: JIOFIN
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NON_EQ_ONLY`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/circulars/CML58021.zip`
- Source SHA-256: `2c7985adfdeb95edba5df9b9300a7de87bf2a58b0b462c20c52b4befb7fb848f`
- Hash matches: `True`
- Missing evidence: change:R-2023-08-21-JIOFIN:RENAME:JIOFIN:INE758E01017: no EQ row with ISIN INE758E01017 for DUMMYREL on the before boundary 2023-08-18 (no row for DUMMYREL in this file (any series)) [a BE row with the ledger ISIN exists] | change:R-2023-08-21-JIOFIN:RENAME:JIOFIN:INE758E01017: identity for DUMMYREL on 2023-08-18 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYREL) | change:R-2023-08-21-JIOFIN:RENAME:JIOFIN:INE758E01017: no EQ row with ISIN INE758E01017 for JIOFIN on the after boundary 2023-08-21 (NO EQ ROW; only series BE) [a BE row with the ledger ISIN exists] | cited circular NSE/CML/58021 does not print the old symbol DUMMYREL | old symbol DUMMYREL is a placeholder: no bhavcopy row and no instrument record before 2023-08-21
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2023-08-21-JIOFIN:RENAME:JIOFIN:INE758E01017`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2025-01-29-ITCHOTELS

- Effective date: `2025-01-29`
- Kind: `RENAME`
- Symbols: ITCHOTELS
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NON_EQ_ONLY`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs06022025_1.pdf`
- Source SHA-256: `60f61a6f41b2aa2f9f769d8fc42c4c090f03ae84b44af62827ea46ccd4d88878`
- Hash matches: `True`
- Missing evidence: change:R-2025-01-29-ITCHOTELS:RENAME:ITCHOTELS:INE379A01028: no EQ row with ISIN INE379A01028 for DUMMYITC on the before boundary 2025-01-28 (no row for DUMMYITC in this file (any series)) [a BE row with the ledger ISIN exists] | change:R-2025-01-29-ITCHOTELS:RENAME:ITCHOTELS:INE379A01028: identity for DUMMYITC on 2025-01-28 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYITC) | change:R-2025-01-29-ITCHOTELS:RENAME:ITCHOTELS:INE379A01028: no EQ row with ISIN INE379A01028 for ITCHOTELS on the after boundary 2025-01-29 (NO EQ ROW; only series BE) [a BE row with the ledger ISIN exists] | old symbol DUMMYITC is a placeholder: no bhavcopy row and no instrument record before 2025-01-29
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2025-01-29-ITCHOTELS:RENAME:ITCHOTELS:INE379A01028`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2025-06-19-ENRIN

- Effective date: `2025-06-19`
- Kind: `RENAME`
- Symbols: ENRIN
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NON_EQ_ONLY`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs25062025_2.pdf`
- Source SHA-256: `dd21c18f5dfcc014cd045c6a574097a8d5cf3f0ef076005bc67f18bab65c883f`
- Hash matches: `True`
- Missing evidence: change:R-2025-06-19-ENRIN:RENAME:ENRIN:INE1NPP01017: no EQ row with ISIN INE1NPP01017 for DUMMYSIEMS on the before boundary 2025-06-18 (no row for DUMMYSIEMS in this file (any series)) [a BE row with the ledger ISIN exists] | change:R-2025-06-19-ENRIN:RENAME:ENRIN:INE1NPP01017: identity for DUMMYSIEMS on 2025-06-18 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYSIEMS) | change:R-2025-06-19-ENRIN:RENAME:ENRIN:INE1NPP01017: no EQ row with ISIN INE1NPP01017 for ENRIN on the after boundary 2025-06-19 (NO EQ ROW; only series BE) [a BE row with the ledger ISIN exists] | old symbol DUMMYSIEMS is a placeholder: no bhavcopy row and no instrument record before 2025-06-19
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2025-06-19-ENRIN:RENAME:ENRIN:INE1NPP01017`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-R-2025-11-12-TMCV

- Effective date: `2025-11-12`
- Kind: `RENAME`
- Symbols: TMCV
- Rows: 1
- membership_evidence_status: `SUFFICIENT`
- identity_evidence_status: `UNKNOWN`
- eq_data_status: `NON_EQ_ONLY`
- owner_membership_recommendation: `ACCEPT_RECOMMENDED` (recommendation only)
- Source: `nse/data/universe/evidence/releases/ind_prs13112025.pdf`
- Source SHA-256: `57dd346835e402f5f5384672f7f7beb71ddf4d67e1af604251fa2ce27b286ea4`
- Hash matches: `True`
- Missing evidence: change:R-2025-11-12-TMCV:RENAME:TMCV:INE1TAE01010: no EQ row with ISIN INE1TAE01010 for DUMMYTATAM on the before boundary 2025-11-11 (no row for DUMMYTATAM in this file (any series)) [a BE row with the ledger ISIN exists] | change:R-2025-11-12-TMCV:RENAME:TMCV:INE1TAE01010: identity for DUMMYTATAM on 2025-11-11 is UNKNOWN_INSTRUMENT isin=None verified=False (no record for DUMMYTATAM) | change:R-2025-11-12-TMCV:RENAME:TMCV:INE1TAE01010: no EQ row with ISIN INE1TAE01010 for TMCV on the after boundary 2025-11-12 (NO EQ ROW; only series BE) [a BE row with the ledger ISIN exists] | old symbol DUMMYTATAM is a placeholder: no bhavcopy row and no instrument record before 2025-11-12
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `change:R-2025-11-12-TMCV:RENAME:TMCV:INE1TAE01010`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

## C. Not-applicable groups (count arithmetic; not membership periods)

Group count: **25**

### G-COUNT-2023-07-20

- Effective date: `2023-07-20`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2023-07-20`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2023-08-21

- Effective date: `2023-08-21`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2023-08-21`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2023-08-24

- Effective date: `2023-08-24`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2023-08-24`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2023-09-07

- Effective date: `2023-09-07`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2023-09-07`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2023-09-29

- Effective date: `2023-09-29`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2023-09-29`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2024-01-05

- Effective date: `2024-01-05`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2024-01-05`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2024-03-28

- Effective date: `2024-03-28`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2024-03-28`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2024-05-15

- Effective date: `2024-05-15`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2024-05-15`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2024-06-07

- Effective date: `2024-06-07`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2024-06-07`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2024-08-30

- Effective date: `2024-08-30`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2024-08-30`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-01-06

- Effective date: `2025-01-06`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-01-06`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-01-10

- Effective date: `2025-01-10`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-01-10`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-01-29

- Effective date: `2025-01-29`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-01-29`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-02-10

- Effective date: `2025-02-10`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-02-10`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-04-07

- Effective date: `2025-04-07`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-04-07`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-04-09

- Effective date: `2025-04-09`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-04-09`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-05-07

- Effective date: `2025-05-07`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-05-07`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-06-16

- Effective date: `2025-06-16`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-06-16`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-06-19

- Effective date: `2025-06-19`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-06-19`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-06-27

- Effective date: `2025-06-27`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-06-27`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-10-14

- Effective date: `2025-10-14`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-10-14`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-10-24

- Effective date: `2025-10-24`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-10-24`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-11-12

- Effective date: `2025-11-12`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-11-12`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-11-17

- Effective date: `2025-11-17`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-11-17`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

### G-COUNT-2025-12-05

- Effective date: `2025-12-05`
- Kind: `COUNT`
- Symbols: 
- Rows: 1
- membership_evidence_status: `NOT_APPLICABLE`
- identity_evidence_status: `NOT_REQUIRED`
- eq_data_status: `NOT_CHECKED`
- owner_membership_recommendation: `N/A` (recommendation only)
- Source: `nse/data/universe/nifty100_count_exceptions.csv`
- Source SHA-256: `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63`
- Hash matches: ``
- Missing evidence: (none listed)
- Periods verified if group alone: (see backlog)
- Exact decision required: write `decision` ACCEPTED or REJECTED on these row_keys only:
  - `exception:2025-12-05`

Do not treat this recommendation as an approval. Membership acceptance is not identity verification and does not certify member-dates.

## D. Contradictory / special rows

Re-check against current backlog and prior Milestone 1 notes (nine contradictory rows called out historically; BAJFINANCE/GRASIM identity ambiguity; VBL 2024-09-12 membership vs OD-PX-2 split parse; dummy-to-listed JIOFIN/ITCHOTELS/ENRIN/TMCV).

Any contradictory row remains fail-closed until the owner decides. No new ledger tokens were written in this programme.

## E. Approval queue reminder

Membership decisions and corporate-action dual-hash approvals are separate queues. Never combine them.
