# P1 Recovery Policy (Session and Database)

**Status:** binding engineering contract for GTF P1  
**Related:** `P1_BACKUP_RESTORE_POLICY.md`, `P1_RECOVERY_PROCEDURES.md`

## Session lifecycle (D57)

Sessions are ephemeral process memory. Digests only are stored (`SessionStore`). The raw token is issued once into an HttpOnly `SameSite=Strict` cookie and is never accepted from query string, JSON body, or `Authorization` headers.

| Event | Behaviour |
|---|---|
| Browser refresh (API up, cookie valid) | Cookie authenticates; no privilege change |
| Cookie missing / expired / forged | `401 UNAUTHENTICATED`; UI may call bootstrap once |
| `POST /api/v1/session/bootstrap` | `replace_all=True`: clears every prior digest, issues one new session; response includes `session_recovery=REBOOTSTRAP`, `durable_state=JOURNAL_ON_DISK` |
| API process restart | All digests lost; stale cookie rejected; journal/plans on disk survive |
| Logout | Revokes current digest and clears cookie |

Stale privileges cannot survive a re-bootstrap beside a new cookie. Concurrent bootstraps are serialised by a store lock; the last successful issue wins.

Session loss is not application readiness. Health/overview continue to derive `data_ready` / `readiness_state` from authoritative limitation signals and remain fail-closed.

## Database recovery

| Concern | Contract |
|---|---|
| Journal writes | `BEGIN IMMEDIATE` before reservation / monthly / open counts |
| Failed writes | No partial journal rows; connection recovers |
| Platform jobs | Stale `RUNNING` → `INTERRUPTED` on startup; never promoted to success |
| Migrations | Versioned under `schema_migration`; replay on connect |
| Backup compatibility | WAL mode + SQLite backup API (see backup policy) |
| Partial commit visibility | Uncommitted rows are invisible after connection close |

## Operator recovery steps

See `P1_RECOVERY_PROCEDURES.md` for the executable checklist. Do not treat a file copy as verified until restore-check passes.

## Limitations

- Sessions do not survive process restart by design.
- No sliding session TTL.
- Log redaction currently focuses on `gtf_session=`; other secret-shaped strings may still appear in exception detail logs behind an `error_id`.
