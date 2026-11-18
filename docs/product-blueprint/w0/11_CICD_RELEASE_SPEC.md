# W0-11 - CI/CD and Release Management Specification

**Status:** Specification only. No deployments or git history mutations authorised in this programme.

## 1. Pipeline stages

1. Lint / typecheck (Python ruff/mypy optional; web tsc).
2. Unit tests: `nse` via `run_all` groups + `platform/tests` + web vitest.
3. Security: dependency scan; secret scan.
4. Build: API image; web static artefacts.
5. Migrate (staging auto; production manual approval).
6. Deploy.
7. Smoke: health + login + one read API.
8. Record release version + SBOM + audit.

## 2. Environments

| Env | Deploy | Data |
|---|---|---|
| local | developer | SQLite/files baseline |
| staging | CI | synthetic/scrubbed |
| production | manual approve | licensed + customers |

## 3. Database migrations

- Expand/contract; never destructive without backup evidence.
- Migration job uses owner role; app role restricted.
- Rollback script or forward-fix required for each migration.

## 4. Feature flags

`GTF_AUTH_MODE`, `GTF_PERSISTENCE`, entitlement flags, module kill switches. Flags logged on boot.

## 5. Versioning

Semver for platform releases; embed git SHA in `/api/v1/meta`. Research methodology version remains separate.

## 6. Rollback

Previous image + DB forward-fix; CDN previous SPA artefacts retained N versions.

## 7. Acceptance

CI blocks merge on failed isolation tests; production deploy requires human approval; no deploy from this specification task.
