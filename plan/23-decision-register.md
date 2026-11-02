# Decision Register & ADRs

## 1. Locked decisions (referenced as D# across the plan set)

| # | Decision | Original ADR owner | Refs |
|---|----------|--------------------|------|
| D1 | Shared schema + tenant/branch discriminators; RLS as last layer | 02, 03, 04 | — |
| D2 | Tenant never from client | 04 §2 | — |
| D3 | Three separate auth realms | 05 | — |
| D4 | One global identity; memberships per tenant | 05, 03 | — |
| D5 | Subdomain-per-tenant + wildcard TLS (irreversible at launch) | 00, 20 §8 | BLOCKING to start DNS early |
| D6 | Platform billing deferred; manual invoices MVP | 06 | — |
| D7 | No Redis/Celery in pilot; Postgres counters | 07 §3 | — |
| D8 | RLS at M5 only, after suite-green | 04 §3, 17 | — |
| D9 | Order quota soft (overage); branch/staff hard | 07 §4 | — |
| D10 | Suspension graceful (in-flight finishes, export always) | 04 §7, 11 §8 | — |
| D11 | Pilot migrates through the same door (Path 1) | 24 §2, 17 | — |
| D12 | Postgres-first; SQLite dropped from migration path | 01 §1 | BLOCKING Phase 0 |
| D13 | One role per membership; per-branch roles discouraged | 09 §4 | — |
| D14 | Module boundaries by bounded context, not layer, enforced structurally | 02 §2, 21 §10 | restructure in Phase 0 |
| D15 | Internal events: typed, versioned, delivered via outbox | 02 §2.3, 13 §0 | — |
| D16 | Outbox worker = in-process asyncio for pilot | 13 §1 | — |

## 2. BLOCKING open decisions (answer before the phase marked)

| # | Question | Default recommendation | Phase that needs it |
|---|----------|------------------------|---------------------|
| O1 | Is the pilot restaurant single- or multi-branch? | Assume single-branch: ship schema (M1–M2), defer branch UI/overrides flow until answer | Phase 1 |
| O2 | Region/URL suitability: will `platform.com` apex serve marketing + subdomain apps? | yes | Phase 0 (DNS) |
| O3 | Suspension grace day-count (7d default?) and "QR stays alive until 24h pre-suspend"? | as stated in 04 §7 | Phase 5 |
| O4 | Retention: audit 7y, payments 7y, platform audit 3y — counsel confirm | as stated | Phase 10 |
| O5 | Commercial: which gateway/countries (Phase 6 trigger) | defer decision until Phase 6 trigger | Phase 6 |
| O6 | End-of-day lock semantics: report snapshot behavior | as 25 §5 | Phase 3 |
| O7 | Waiter-request device ownership: who claims, floor-manager escalation config defaults | 13 §6 | Phase 8 |
| O8 | Does the pilot restaurant need staff scheduling/shifts at launch? (affects the membership model — confirm with the pilot customer before Phase 1 modelling) | assume **no** (§3.1 deferral below stands) | Phase 1 |

## 3. Deferred-by-design (each gets an ADR before build, not before now)

Per-tenant custom domains · marketplaces/integrations · tenant API keys/webhooks · staff scheduling/shifts (see O8 — confirm with pilot) · multi-region/residency · split-bill UI · kitchen stations · scheduled menus/time windows · custom roles · impersonation · white-label staff app · platform feature-flag manager UI · analytics store (separate from OLTP).

### 3.1 Explicitly deferred workflows (chosen omissions, not forgotten ones)

| Workflow | Status | One-line justification |
|----------|--------|------------------------|
| Multi-language menu | Deferred | Tourist-facing tenants will want it, but it touches menu schema, QR surface, and translations — ADR before any build; not MVP-blocking. |
| Staff scheduling / shifts | Deferred — **confirm with pilot first (O8)** | Impacts the membership/branch-scope model, so the pilot customer must be asked before Phase 1 modelling; if the pilot needs it, we re-plan rather than retrofit. |
| Table transfer / merge | Deferred | Single-table dining sessions keep the bill model simple; transfer/merge adds multi-table session state that nothing in the MVP consumes. |
| Gift cards / pre-paid credits | Deferred | Creates a liability/accounting surface (issuance, redemption, expiry, reporting) that belongs with Phase 6 payments, never before billing exists. |
| Tax remittance tracking | Deferred | Reports expose tax collected per period (25), but per-jurisdiction remittance bookkeeping is compliance-specific — ADR per target jurisdiction before build. |
| Per-branch printer / device configuration | Deferred | 09 §3 models kitchen stations conceptually; actual per-branch printer mapping/device drivers need real pilot hardware requirements first. |
| Smart cash-drawer hardware integration | Deferred | The drawer *counting/reconciliation workflow* is built (25 §5); only the automated hardware (ejection/sensors) is out of scope. |

## 4. ADR template (use per decision; store in `docs/adr/ADR-###.md`)

```
# ADR-<n>: <title>
Status | Date | Deciders
Context: problem + constraints
Decision: chosen option (one sentence)
Options considered: A/B/C with pros/cons (table)
Consequences: what gets easier/harder; migration needs
Links: plan file refs (e.g. plan/04 §3)
```

## 5. Change control for this plan set

- Any change to D# requires a new ADR + `00-MASTER-PLAN` mirror update; plan files stay the contract (`baseplan.md` historical only).
- Resolve open questions via PR editing `23 §2` row → moves to §1 as new locked D# with refs.
