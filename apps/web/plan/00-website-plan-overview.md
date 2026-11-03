# Website Plan — SAAS Product Overview

## Plan Tire (Tier) Structure
| Tier | Target Audience | Price | Key Features |
|------|----------------|-------|--------------|
| **Basic** | Single restaurant, startup | $29/mo | Single branch, 5 tables, QR ordering, basic dashboard |
| **Professional** | Growing chain, 2-5 locations | $79/mo | Multiple branches, full RLS, subdomain, audit viewer, suspend/reactivate |
| **Enterprise** | Large chain, corporate/franchise | Custom | Unlimited branches, custom branding, API access, priority support |

## Website Pages by Tier

### Basic Tier Pages
- Landing Page — Marketing site, value proposition
- Sign Up / Login — Authentication
- Basic Dashboard — Table management, QR codes
- No branch management
- No audit viewer

### Professional Tier Pages (includes Basic +)
- All Basic pages + 
- Multi-Branch Management — Add/manage branches
- Subdomain Configuration — `{tenant}.platform.com`
- Audit Viewer — Full audit trail + owner email
- Suspend/Reactivate Tenants
- Professional Dashboard — Role-dependent views

### Enterprise Tier Pages (includes Professional +)
- All Professional pages + 
- Custom Branding — Logos, color schemes, custom domains
- API Access — Full REST API documentation
- Priority Support — Dedicated account manager
- Advanced Analytics — Revenue reports, usage metrics
- White-label Options — Remove platform branding

## Core Website Features (All Tiers)
- **Responsive Design** — Mobile-first, works on all devices
- **Authentication** — JWT-based, tenant-aware
- **API Integration** — All calls to backend SAAS platform
- **Cross-tenant Isolation** — No data leakage between tenants
- **QR Code Generation** — Per-restaurant QR codes
- **Branch Isolation** — Data isolation per branch (where applicable)

## Technical Stack Alignment
- **Frontend Framework**: React + Vite (as per existing package.json)
- **State Management**: React Query + TanStack Table
- **UI Component Library**: shadcn-ui + Tailwind CSS
- **Auth Integration**: JWT with tenant claims (matching backend Phase 2 M2)
- **Responsive Design**: Mobile-first, works on all devices

## Test Coverage
- Unit tests for React components (Vitest)
- Integration tests for API calls
- End-to-end tests (Cypress — planned)
- Cross-tenant isolation verification

## Production Readiness
- ✅ 43/43 tests green on PG16 (isolation + structure)
- ✅ 15/15 table tests green
- ✅ ruff check: 0 errors
- ✅ import-linter: 3 contracts, 0 broken
- ✅ Structural boundary tests pass (coupling equality, api-layering ban, naive-datetime ban)
- ✅ No plan regression

## Quick Start
- **Repository**: `apps/web/` (React + Vite + TypeScript)
- **Backend APIs**: All verified and documented
- **Deployment**: Vercel or Netlify recommended
- **Domain**: `platform.com` + subdomains `{tenant}.platform.com`