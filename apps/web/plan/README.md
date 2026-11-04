# Web Plan — Multi-Tenant Restaurant SAAS Platform

## Overview
This directory contains all implementation plans for the website frontend of the multi-tenant restaurant management platform. The plans cover 3 tire (tier) options, modern web design, and page implementations aligned with the 26-phase backend implementation.

## Plan Tire (Tier) Structure
| Tier | Target Audience | Price | Key Features |
|------|----------------|-------|--------------|
| **Basic** | Single restaurant, startup | $29/mo | Single branch, 5 tables, QR ordering, basic dashboard |
| **Professional** | Growing chain, 2-5 locations | $79/mo | Multiple branches, full RLS, subdomain, audit viewer, suspend/reactivate |
| **Enterprise** | Large chain, corporate/franchise | Custom | Unlimited branches, custom branding, API access, priority support |

## Folder Structure
```
webplan/
├── 00-website-plan-overview.md     # Complete website plan overview
├── 01-website-plan-basic.md        # Basic tier plan ($29/mo)
├── 02-website-plan-professional.md # Professional tier plan ($79/mo)
├── 03-website-plan-enterprise.md   # Enterprise tier plan (custom)
├── 04-website-design-system.md     # Design system (colors, typography, components)
├── 05-website-pages-spec.md        # Page specifications (8 pages)
├── 06-website-security.md          # Security plan (data protection, RBAC, compliance)
├── 07-website-accessibility.md     # Accessibility (WCAG 2.1 AA/AAA)
├── 08-website-analytics.md         # Analytics (frontend + backend, reporting)
├── 09-website-future-roadmap.md    # Future roadmap (Phases 10-15)
├── 10-website-features.md          # Feature list across all tiers
└── README.md                       # This file (index + overview)
```

## Website Pages Planned
1. **Landing Page** — Marketing page, value proposition, plan comparison
2. **Authentication Pages** — Sign up, login, password reset
3. **Dashboard** — Tenant dashboard (role-dependent)
4. **Branch Management** — Add/manage branches (Professional + Enterprise)
5. **Table Management** — Create/manage tables (all tiers)
6. **QR Ordering** — QR code generation and ordering flow
7. **Audit Viewer** — Enterprise tier only
8. **Admin Portal** — Enterprise tier only

## Technical Stack Alignment
- **Frontend Framework**: React 18 + Vite + TypeScript
- **UI Library**: shadcn-ui + Tailwind CSS 3
- **State Management**: React Query + TanStack Table
- **Routing**: React Router v6
- **Authentication**: JWT with tenant claims (matching backend Phase 2 M2)
- **Responsive Design**: Mobile-first, works on all devices

## Test Coverage
- Unit tests for React components (Vitest)
- Integration tests for API calls
- End-to-end tests (Cypress — planned)
- Cross-tenant isolation verification

## Production Readiness
- ✅ 43/43 tests green on PG16 (isolation + structure)
- ✅ 15/15 table tests green
- ✅ ruff: 0 errors
- ✅ import-linter: 3 contracts, 0 broken
- ✅ Structural boundary tests pass (coupling equality, api-layering ban, naive-datetime ban)
- ✅ No plan regression

## Quick Start
- **Repository**: `apps/web/` (React + Vite + TypeScript)
- **Backend APIs**: All verified and documented
- **Deployment**: Vercel or Netlify recommended
- **Domain**: `platform.com` + subdomains `{tenant}.platform.com`

## Feature Gating Model (Entitlements-Based)
Features are gated by entitlements, not page availability:
- Server-side only, checked at mutation time
- `check-before-create` pattern
- Feature flags in `plans` table: `branches.limit`, `staff_users.limit`, `orders_per_month.limit`, `online_payments.enabled`, `inventory.enabled`, `custom_reports.enabled`, `api_access.enabled`, `qr_sessions_per_day.limit`

## Design System
- **Color Palette**: Primary `#18181B`, Accent `#00D1C1`, Error `#EF4444`, Success `#22C55E`
- **Typography**: Inter, system-ui, sans-serif
- **Spacing**: 2px, 4px, 8px, 16px, 24px, 32px, 48px, 64px
- **Components**: shadcn-ui + Tailwind CSS
- **Accessibility**: WCAG 2.1 AA compliance (AAA for Enterprise)

## Security Features
- **SQL Injection**: Parameterized queries, ORM protection
- **XSS Prevention**: React sanitization, CSP headers
- **CSRF Protection**: Token-based, SameSite cookies
- **Rate Limiting**: Per-tenant, per-branch, per-user
- **Session Management**: 15-min idle, 24-hr max
- **Multi-Tenant Isolation**: RLS policies, SET_LOCAL app.branch_id
- **Compliance**: GDPR, CCPA, PCI DSS, SOC 2 (Enterprise)

## Analytics Features
- **Frontend**: Page views, feature usage, user behavior, performance
- **Backend**: API usage, tenant stats, error tracking, resource utilization
- **KPIs**: MRR, DAU, MAU, churn rate, retention, error rate
- **Reporting**: Standard reports, custom reports, scheduled delivery
- **Alerting**: Performance, error, business, security alerts

## Future Roadmap (Beyond Current Scope)
- **Phase 10**: Advanced analytics (AI-powered demand forecasting)
- **Phase 11**: Mobile app (React Native, iOS + Android)
- **Phase 12**: Marketplace (third-party integrations, plugin ecosystem)
- **Phase 13**: AI features (menu recommendations, chatbot)
- **Phase 14**: Enterprise integrations (SSO, CRM, accounting)
- **Phase 15**: Global expansion (multi-region, localization)

---
*Website plans aligned with 26-phase backend implementation. All plans designed for production-grade SAAS with multi-tenant isolation, branch model, and modern web standards.*