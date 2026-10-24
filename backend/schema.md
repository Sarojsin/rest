# Backend Schema Implementation Rules

This file is the implementation companion to [`../docs/schema.md`](../docs/schema.md). The shared schema document defines the domain contract; this file defines how to implement it safely with SQLAlchemy 2.x and Alembic.

## ORM rules

- Use SQLAlchemy 2.x typed declarative mappings (`Mapped[...]`, `mapped_column`) and explicit relationship/loading behavior.
- Use PostgreSQL UUID, `TIMESTAMPTZ`, `NUMERIC`, JSONB, database enums/check constraints, unique constraints, and foreign keys intentionally.
- Do not use ORM model classes as request/response DTOs. Use Pydantic request and response schemas.
- Add `restaurant_id` and tenant-aware relationship constraints to tenant-owned records. Ensure composite constraints are represented in both the migration and model metadata when practical.
- Name constraints and indexes predictably, e.g. `uq_orders_restaurant_idempotency_key`, `ix_orders_restaurant_status_submitted_at`, `fk_orders_restaurant_table`.
- Use explicit `ondelete` behavior. Do not cascade-delete financial or audit history.
- Avoid implicit lazy-loading during response serialization. Select required relations explicitly to prevent N+1 queries.
- Do not expose ORM entities directly from endpoints; map to response DTOs with only authorized fields.

## Session and transaction rules

- One request-scoped SQLAlchemy session/unit-of-work; close it reliably.
- Service functions own the transaction boundary for a business operation. Avoid deep helpers that each start/commit their own transactions.
- Do not commit inside a generic repository helper.
- Do not make network calls to payment providers while holding a database transaction open.
- Lock the rows or use version-checked updates required by the invariant. Use `SELECT ... FOR UPDATE` where justified and test concurrency under PostgreSQL.
- Avoid synchronous blocking I/O inside `async def`. Choose either a well-understood synchronous SQLAlchemy pattern in synchronous endpoints or an async driver/session consistently; do not mix casually.

## Alembic rules

- Schema changes are migrations, not `Base.metadata.create_all()` in deployed environments.
- Review generated migrations; autogeneration is not a substitute for review.
- Every migration must include named constraints, correct FK/index order, safe nullability transition, and a downgrade or documented forward-only recovery plan.
- Large/backfilled changes need an expand/backfill/contract rollout. Do not add a non-null column without a safe default/backfill sequence on a live table.
- Avoid index creation that blocks writes when a concurrent index is appropriate; account for Alembic transaction limitations.
- Test migration from an empty DB and from the previous release schema.

## Query rules

- Scope every tenant query using the trusted restaurant context. Do not accept a `restaurant_id` query parameter as proof of access.
- Prefer explicit column selection and bounded pagination.
- Never perform N+1 loops across database queries for kitchen lists, menu pages, or reports.
- Escape/parameterize filters; whitelist sortable field names.
- Write integration tests against PostgreSQL for enums, partial indexes, locking, JSONB, and concurrency behavior; SQLite-only tests are insufficient for those features.
