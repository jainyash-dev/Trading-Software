# Post-change validation

**Dated 2026-11-11. Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`.**

No approved ledger edit was supplied. No eligibility code was changed. Membership conversion was not run.

`python3 -m nse.validation.run_all` was not repeated. The suite on 2026-11-11 ran 1,313 tests with 1 failure, `test_repo.Repo.test_root_matches_the_reel`, caused by a root `.DS_Store`. That file was removed and the single test passed. This batch did not create a new full-suite result.

Eligible symbol-dates remain 0. The matrix in `P0_RESEARCH_ELIGIBILITY_MATRIX.csv` is unchanged: 123,778 member-dates, all `EXCLUDED_MEMBERSHIP`, because the 271 decisions are blank.

P0 is not complete.
