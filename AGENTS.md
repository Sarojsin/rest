# Repository-Wide Engineering Rules

Follow all rules in the docs/. Also see backend/AGENTS.md, apps/web/AGENTS.md, apps/mobile/AGENTS.md.

Key invariants:
- PostgreSQL is the source of truth.
- QR orders require staff confirmation.
- Money in integer minor units.
- Audit logs append-only.
- Tenant-scoped.

