# 14 - W0 Technology Decision Register

Status: `RECOMMENDED` | `CURRENT` | `PENDING_OWNER` | `DECLINED` | `OWNER_DIRECTION`

| ID | Topic | Choice | Status |
|---|---|---|---|
| W0-TD-PKG | Commercial packaging | Cloud browser SaaS | OWNER_DIRECTION (OD-BP-001) |
| W0-TD-LOCAL | Local baseline | Loopback + SQLite allowed for eng | OWNER_DIRECTION (OD-BP-001) |
| W0-TD-API | API framework | FastAPI modular monolith | RECOMMENDED + CURRENT |
| W0-TD-FE | Frontend | React/TS/Vite | RECOMMENDED + CURRENT |
| W0-TD-DB | SaaS DB | PostgreSQL managed + RLS | RECOMMENDED; OD-BP-008 |
| W0-TD-CACHE | Cache/queue | Redis managed | RECOMMENDED |
| W0-TD-OBJ | Objects | S3-compatible versioned | RECOMMENDED |
| W0-TD-AUTH | Identity stack | Self-op vs managed IdP | PENDING_OWNER (OD-BP-004) |
| W0-TD-MFA | MFA | TOTP | PENDING_OWNER (OD-BP-004) |
| W0-TD-PSP | Payments | Stripe/Razorpay/other | PENDING_OWNER (OD-BP-005) |
| W0-TD-CLOUD | Provider/region | Major cloud India-preferring | PENDING_OWNER (OD-BP-010) |
| W0-TD-EDGE | CDN/WAF | Required for public SaaS | RECOMMENDED |
| W0-TD-DESK | Desktop shells | Not commercial | DECLINED |
| W0-TD-BROKER | Order APIs | Absent | DECLINED |
| W0-TD-DUALWRITE | SQLite+Postgres dual-write | Not default | DECLINED unless consistency design approved |

No purchase or provider commitment is made by this register.
