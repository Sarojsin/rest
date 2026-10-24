# Restaurant Management System — Engineering Specification Pack

**Status:** Planning baseline, not an implementation or a claim of production certification  
**Updated:** 24 October 2026  
**Product:** Dine-in restaurant management; one pilot restaurant, then reusable commercial product

This folder contains implementation guidance for a React website, a React Native staff app, and a FastAPI backend. The files describe the proposed baseline, the confirmed product decisions, and the decisions still requiring validation with the pilot restaurant.

## Start here

1. Read [`docs/product-decisions.md`](docs/product-decisions.md) to distinguish confirmed decisions from recommendations and unresolved questions.
2. Read [`docs/product-planning.md`](docs/product-planning.md) for the original product plan and [`docs/architecture.md`](docs/architecture.md) for the proposed system boundaries and deployment model.
3. Read [`docs/schema.md`](docs/schema.md) before designing ORM models or migrations.
4. Read [`docs/api-contracts.md`](docs/api-contracts.md) before building clients or endpoint implementations.
5. Read [`docs/security-and-operations.md`](docs/security-and-operations.md) before implementing authentication, tenancy, payments, deployment, or observability.
6. Follow the root [`AGENTS.md`](AGENTS.md) and the app-specific rules in `backend/AGENTS.md`, `apps/web/AGENTS.md`, and `apps/mobile/AGENTS.md`.

## Proposed repository layout

```text
restaurant-management/
├── AGENTS.md
├── README.md
├── docs/
│   ├── product-planning.md
│   ├── product-decisions.md
│   ├── architecture.md
│   ├── schema.md
│   ├── api-contracts.md
│   └── security-and-operations.md
├── backend/
│   ├── AGENTS.md
│   └── schema.md
└── apps/
    ├── web/
    │   └── AGENTS.md
    └── mobile/
        └── AGENTS.md
```

This is a specification layout, not a generated source-code repository. Create code and configuration only after confirming the open requirements and selecting a concrete dependency/tooling baseline.

## Baseline technology recommendations

- **Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL.
- **Web:** React + TypeScript; responsive customer QR menu/order flow and owner/manager web experience where needed.
- **Mobile:** React Native + TypeScript for waiter, kitchen, and cashier role-based experiences.
- **API:** Versioned JSON REST API under `/api/v1`; OpenAPI is the contract source for generated TypeScript types/clients.
- **Operational data:** PostgreSQL is the source of truth. Redis may support rate limiting, short-lived caches, and coordination; it must not be the only store for orders, payments, or kitchen state.
- **Background work:** Use a durable job/outbox design for work that must survive process restarts. Select a queue implementation when deployment requirements are known.

The application frameworks are confirmed: React website, React Native staff app, and FastAPI backend. The libraries and operational choices listed above are recommendations that still need approval. Confirm dependency versions, hosting, payment gateway, authentication, tax configuration, and offline requirements before implementation. Pin dependencies and keep lockfiles committed.

## Important limitation

These documents are production-oriented design rules, not a substitute for testing, a security review, legal/tax/accounting validation, payment-gateway certification, or observing the pilot restaurant. Do not interpret “production-ready” as meaning a system is safe to deploy solely because the Markdown files exist.
