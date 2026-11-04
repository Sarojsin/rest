# 10 — Parking Lot and Scope-Change Intake

**Purpose:** capture every good idea that is not in the active phase, so it stops competing with the work in front of us.

**Rule:** an item in this file is **not** committed work. It is a recorded option. Nothing here enters a phase without the promotion process in §4.

---

## 1. Intake rules

1. Any new idea gets an ID (`PL-xxx`), a one-line value statement, and a proposed priority.
2. If the idea is a bug or a security issue in shipped code, it is not parked — it goes to the normal defect process.
3. If the idea is required by a signed customer contract, record the contract date and mark it `CONTRACTUAL`; it still needs an ADR and a scope trade.
4. Do not estimate items in detail at intake. A rough size (`S/M/L/XL`) is enough.
5. Review the parking lot at phase boundaries, not during a phase.
6. Rejected items stay with a `REJECTED` note and the reason, so they are not re-litigated every month.

## 2. Item template

```md
### PL-xxx — Title

- **Value:**
- **Priority guess:** P2 | P3 | NO
- **Size:** S | M | L | XL
- **Dependencies:**
- **Why parked:**
- **Promotion trigger:**
- **Decision:** OPEN | PROMOTED (PA-x) | REJECTED
- **Notes:**
```

## 3. Parked items

### PL-001 — Payment gateway (Stripe or local provider)

- **Value:** automatic card/wallet payments and renewals.
- **Priority guess:** P3 (master plan D6 defers it).
- **Size:** XL.
- **Dependencies:** webhook endpoint, signature verification, reconciliation, PCI scope review, provider account.
- **Why parked:** no gateway exists; manual billing covers the first tenants.
- **Promotion trigger:** ≥5 tenants paying manually and a provider contract.
- **Decision:** OPEN.

### PL-002 — Automatic renewal and dunning

- **Value:** reduce manual renewal work and involuntary churn.
- **Priority guess:** P2.
- **Size:** L.
- **Dependencies:** worker/scheduler, email, payment gateway or manual reminder flow.
- **Why parked:** no worker; PA-1 uses a due-invoice list.
- **Promotion trigger:** first renewal cycle with >10 tenants.
- **Decision:** OPEN.

### PL-003 — Email delivery (invitations, notices, reminders)

- **Value:** remove manual copy/paste onboarding and suspension notices.
- **Priority guess:** P2.
- **Size:** M.
- **Dependencies:** transport, templates, retry, delivery log, unsubscribe/preferences.
- **Why parked:** PA-ADR-004 keeps MVP infrastructure-free.
- **Promotion trigger:** first external tenant onboarding.
- **Decision:** OPEN.

### PL-004 — Support tickets and messages

- **Value:** replace ad-hoc support with a tracked queue.
- **Priority guess:** P2.
- **Size:** L.
- **Dependencies:** email or in-app notifications, tenant-visible replies, attachments (object storage), SLA fields.
- **Why parked:** audit + diagnostics answer the first support cases.
- **Promotion trigger:** support volume exceeds 2 hours/week or a support contract requires it.
- **Decision:** OPEN.

### PL-005 — Announcements and notification center

- **Value:** communicate maintenance, policy changes, and product news.
- **Priority guess:** P2.
- **Size:** M.
- **Dependencies:** email/in-app delivery, audience targeting, read receipts.
- **Why parked:** no delivery infrastructure.
- **Promotion trigger:** PA-2 notification service exists.
- **Decision:** OPEN.

### PL-006 — Onboarding funnel monitoring

- **Value:** identify where new tenants abandon setup.
- **Priority guess:** P2.
- **Size:** M.
- **Dependencies:** onboarding events/analytics, checklist state.
- **Why parked:** no event tracking yet.
- **Promotion trigger:** ≥10 signups with measurable drop-off.
- **Decision:** OPEN.

### PL-007 — Feature flags and tenant targeting

- **Value:** staged rollout and per-plan feature control.
- **Priority guess:** P2.
- **Size:** M.
- **Dependencies:** flag table, evaluation cache, tenant targeting, admin UI.
- **Why parked:** entitlements JSON covers plan-level features in MVP.
- **Promotion trigger:** first risky feature rollout or enterprise override request.
- **Decision:** OPEN.

### PL-008 — Integration management

- **Value:** configure and monitor third-party integrations.
- **Priority guess:** P2.
- **Size:** L.
- **Dependencies:** provider configs, secret storage, webhook event log, health checks.
- **Why parked:** no integrations to manage yet.
- **Promotion trigger:** first integration contract.
- **Decision:** OPEN.

### PL-009 — Incident and maintenance management

- **Value:** track platform incidents, maintenance windows, and recovery times.
- **Priority guess:** P2.
- **Size:** M.
- **Dependencies:** status page or notification channel, incident table, on-call process.
- **Why parked:** process before tool.
- **Promotion trigger:** first production incident requiring customer communication.
- **Decision:** OPEN.

### PL-010 — Backup monitoring

- **Value:** prove backups exist and restores work.
- **Priority guess:** P2.
- **Size:** S–M.
- **Dependencies:** infrastructure backup job and a status source.
- **Why parked:** infrastructure work precedes UI.
- **Promotion trigger:** production launch / first restore drill.
- **Decision:** OPEN.

### PL-011 — Advanced analytics and exports

- **Value:** cohorts, plan mix, churn reasons, revenue by period, CSV/Excel exports.
- **Priority guess:** P2.
- **Size:** L.
- **Dependencies:** event history, rollup tables, export service.
- **Why parked:** the PA-1 dashboard covers the launch metrics.
- **Promotion trigger:** board/investor reporting need.
- **Decision:** OPEN.

### PL-012 — Branch overview across tenants

- **Value:** read-only branch map/list for support and ops.
- **Priority guess:** P2.
- **Size:** S–M.
- **Dependencies:** tenant directory service, branch counts.
- **Why parked:** tenant detail already shows counts.
- **Promotion trigger:** support needs cross-tenant branch lookup.
- **Decision:** OPEN.

### PL-013 — Time-limited, read-only impersonation

- **Value:** faster support for tenant-specific UI issues.
- **Priority guess:** P3.
- **Size:** L.
- **Dependencies:** scoped tokens, tenant notice, time limit, read-only enforcement, dedicated audit, security review.
- **Why parked:** highest-risk feature in the spec; explicitly excluded by plan 08.
- **Promotion trigger:** support contract requiring it + completed threat model.
- **Decision:** OPEN (not approved).

### PL-014 — Promotions, coupons, and referrals

- **Value:** acquisition and discount campaigns.
- **Priority guess:** P3.
- **Size:** L.
- **Dependencies:** invoice discount engine, redemption limits, referral tracking, fraud rules.
- **Why parked:** manual discounts on invoice lines cover early deals.
- **Promotion trigger:** paid marketing launch.
- **Decision:** OPEN.

### PL-015 — Website CMS

- **Value:** edit marketing content from the admin.
- **Priority guess:** P3.
- **Size:** L.
- **Dependencies:** content model, media storage, preview/publish workflow.
- **Why parked:** separate product surface.
- **Promotion trigger:** marketing team requests it and owns content operations.
- **Decision:** OPEN.

### PL-016 — Developer API and API keys

- **Value:** let tenants integrate POS/accounting.
- **Priority guess:** P3.
- **Size:** XL.
- **Dependencies:** API key model, scopes, rate limits, docs, sandbox, versioning.
- **Why parked:** no external demand yet; entitlements `api_access` is a stub.
- **Promotion trigger:** first signed integration partner.
- **Decision:** OPEN.

### PL-017 — Data governance, deletion, and export workflows

- **Value:** GDPR/privacy requests, tenant offboarding, retention enforcement.
- **Priority guess:** P3.
- **Size:** L.
- **Dependencies:** data map, export jobs, deletion approvals, legal review, audit.
- **Why parked:** no hard-delete in MVP; archive only.
- **Promotion trigger:** first deletion request or regulatory requirement.
- **Decision:** OPEN.

### PL-018 — Automated payment reconciliation

- **Value:** match bank/provider statements to invoices automatically.
- **Priority guess:** P3.
- **Size:** L.
- **Dependencies:** gateway/bank feed, matching rules, exception queue.
- **Why parked:** manual confirmation is auditable and sufficient at pilot volume.
- **Promotion trigger:** >100 payments/month.
- **Decision:** OPEN.

### PL-019 — Customer-success automation

- **Value:** health scores, churn-risk alerts, lifecycle playbooks.
- **Priority guess:** P3.
- **Size:** L.
- **Dependencies:** usage analytics, event history, CRM or task system.
- **Why parked:** needs product usage data that does not exist yet.
- **Promotion trigger:** dedicated CS hire.
- **Decision:** OPEN.

### PL-020 — Tenant staff and branch editing from the platform

- **Value:** operators could fix tenant data directly.
- **Priority guess:** NO.
- **Size:** L.
- **Dependencies:** fine-grained impersonation/authorization, tenant notice, audit.
- **Why parked:** violates the product principle that owners operate their restaurants; support uses diagnostics.
- **Promotion trigger:** only with a new ADR and explicit tenant consent design.
- **Decision:** REJECTED for PA-1/PA-2.

### PL-021 — SSO for platform admins

- **Value:** central identity, faster offboarding.
- **Priority guess:** P3.
- **Size:** M.
- **Dependencies:** IdP, SAML/OIDC, group-to-role mapping.
- **Why parked:** four named admins do not need SSO yet.
- **Promotion trigger:** platform team >10, a chain/enterprise customer with a centralized IdP requirement, or a specific Microsoft Entra ID/Google Workspace/SAML/OIDC request.
- **Decision:** DEFERRED — **not committed to PA-3** and not part of any current pricing/scope promise. Keep the auth module clean so it can be added later.

### PL-022 — Usage-based billing and overage invoices

- **Value:** charge for orders/branches above plan limits.
- **Priority guess:** P2–P3.
- **Size:** L.
- **Dependencies:** `usage_counters`, entitlement enforcement, invoice line generation.
- **Why parked:** entitlement enforcement is a stub; no usage data yet.
- **Promotion trigger:** first tenant exceeding a soft limit.
- **Decision:** OPEN.

### PL-023 — Tax/VAT invoices

- **Value:** compliant invoices per jurisdiction.
- **Priority guess:** P2.
- **Size:** M.
- **Dependencies:** tax rules, issuer/PAN/VAT configuration, invoice templates, legal review by a Nepali tax professional.
- **Why parked:** PA-1 ships **configurable platform invoice templates** with `tax_treatment=UNCONFIRMED`; it does not claim tax compliance. Full jurisdiction-specific compliance (including restaurant sales invoices and any IRD e-invoicing/CBMS requirement) needs professional review.
- **Promotion trigger:** first jurisdiction/tax sign-off requiring a compliant template, or a regulator requiring e-invoicing.
- **Decision:** OPEN — PA-1 supports the fields; legal/compliance sign-off is a separate gate.

### PL-024 — Multi-currency plans

- **Value:** sell in more than one currency.
- **Priority guess:** P2.
- **Size:** M.
- **Dependencies:** FX policy, plan price per currency, reporting normalization.
- **Why parked:** the MVP launch currency is NPR (D-2); no FX policy or cross-currency reporting.
- **Promotion trigger:** first non-NPR customer.
- **Decision:** OPEN.

### PL-025 — Mobile admin app

- **Value:** suspend a tenant from a phone.
- **Priority guess:** NO.
- **Size:** L.
- **Dependencies:** mobile shell, push, offline handling.
- **Why parked:** responsive web covers emergency use.
- **Promotion trigger:** none planned.
- **Decision:** REJECTED for now.

### PL-026 — Public status page

- **Value:** customer-facing uptime communication.
- **Priority guess:** P2.
- **Size:** S–M.
- **Dependencies:** health data, incident records, hosting.
- **Why parked:** no incidents process yet.
- **Promotion trigger:** PA-2 incident management.
- **Decision:** OPEN.

### PL-027 — White-label / reseller mode

- **Value:** let partners resell the platform.
- **Priority guess:** P3.
- **Size:** XL.
- **Dependencies:** tenancy hierarchy, branding, revenue share, partner billing.
- **Why parked:** changes the business model and schema.
- **Promotion trigger:** signed reseller agreement.
- **Decision:** OPEN.

### PL-028 — Data warehouse export

- **Value:** BI and long-term analytics.
- **Priority guess:** P3.
- **Size:** M–L.
- **Dependencies:** event schema, ETL, privacy review.
- **Why parked:** no warehouse.
- **Promotion trigger:** investor/BI requirement.
- **Decision:** OPEN.

### PL-029 — AI support assistant

- **Value:** draft replies from audit/diagnostics data.
- **Priority guess:** NO.
- **Size:** L.
- **Dependencies:** support tickets, redaction, evaluation, data policy.
- **Why parked:** no support corpus; high privacy risk.
- **Promotion trigger:** none planned.
- **Decision:** OPEN (not approved).

### PL-030 — Audit streaming to SIEM

- **Value:** security monitoring and long-term retention.
- **Priority guess:** P3.
- **Size:** S–M.
- **Dependencies:** append-only export, SIEM contract.
- **Why parked:** DB audit + export is enough for the pilot.
- **Promotion trigger:** SOC2/ISO or enterprise security requirement.
- **Decision:** OPEN.

## 4. Promotion process

An item can enter a phase only when all are true:

1. **Demand evidence:** a customer, contract, incident, or measured metric, not “it would be nice”.
2. **ADR:** written in `09-risks-and-decisions.md`, status `Accepted`.
3. **Scope trade:** something of equal or greater size is removed from the phase, or the phase estimate and end date are explicitly extended.
4. **Design:** data model + API contract updated in `04`/`05`.
5. **Test plan:** acceptance cases added to `08-testing-and-acceptance.md`.
6. **Sign-off:** product + tech lead + (for security-sensitive items) security reviewer.

If any of the six is missing, the item stays parked. “We will do it quickly” is not evidence.

## 5. Review cadence

- **Phase boundary:** review the whole list, promote at most two items into the next phase.
- **Monthly:** update decision status; close items that are no longer relevant.
- **Quarterly:** re-check P3 items against business goals; reject stale items.
- **Never mid-sprint:** no scope changes during a sprint except security or data-loss defects.

## 6. Explicit “do not build yet” list

Even if requested in passing, these are not PA-1 work:

- impersonation,
- gateway payments,
- automatic dunning,
- support tickets,
- CMS,
- developer API,
- tenant staff/branch editing,
- AI features,
- mobile admin app,
- white-label/reseller,
- data deletion console.
