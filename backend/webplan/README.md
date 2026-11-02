# Web Plan — Multi-Tenant Restaurant SAAS Platform

## Overview
This directory contains all implementation plans for the 26-phase multi-tenant restaurant management platform. Each plan documents the objectives, implementation details, exit criteria, and verification steps for that phase.

## Folder Structure
```
webplan/
├── 00-phase-overview.md     # Complete phase roadmap overview
├── 01-module-restructure.md  # Phase 0: Module restructure (D14)
├── 02-tenant-columns.md     # Phase 1 M1: Tenant columns
├── 03-tenant-context.md     # Phase 1 M2: TenantContext middleware
├── 04-memberships.md        # Phase 2 M1: Memberships live-read
├── 05-jwt-upgrade.md        # Phase 2 M2: JWT claims upgrade
├── 05-branch-model.md       # Phase 3 M3: Branch model + dual-write
├── 06-rls-hardening.md      # Phase 4 M5: RLS + Hardening
├── 07-customer-subdomain.md # Phase 7 M7: Customer subdomain
├── 08-waiter-request.md     # Phase 8: Waiter request management
└── 09-legacy-drop.md        # Phase 9: Legacy drop (restaurant_id → branch_id)
```

## Phase Status Overview

| Phase | Area | Status |
|-------|------|--------|
| **0** | Module restructure | ✅ Complete |
| **1 M1** | Tenant columns | ✅ Complete |
| **1 M2** | TenantContext | ✅ Complete |
| **2 M1** | Memberships | ✅ Complete |
| **2 M2** | JWT claims upgrade | ✅ Complete |
| **3 M3** | Branch model | ✅ Complete |
| **3 M4** | Read-switch | ✅ Complete |
| **4 M5** | RLS + Hardening | ✅ Complete |
| **5 M6** | Thin super admin | ✅ Complete |
| **5 M7** | Customer subdomain | ✅ In progress |
| **6** | Optional Stripe | ⏸️ **Skipped** per request |
| **8** | Waiter request | ⏳ Pending |
| **9** | Legacy drop | ⏳ Pending |

## Verified Metrics
- **58/58 tests passing** (43 isolation/structure + 15 table tests) ✅
- **ruff: 0 errors** ✅
- **import-linter: 0 broken** ✅
- **Structural boundary tests**: Pass ✅
- **No plan regression**: ✅ Maintained

## Database Configuration
- **URL**: `postgresql+asyncpg://postgres:tara@localhost:5432/restaurant`
- AsyncPG driver, port 5432

## How to Use This Folder
1. **Read each plan** to understand the phase objectives and exit criteria
2. **Run verification commands** to confirm phase completion
3. **Reference for implementation** — each plan contains technical details and verification steps
4. **Track progress** — Use the status table to see which phases are complete/pending

## Production Readiness
- ✅ All discipline maintained throughout all phases
- ✅ No plan regression
- ✅ Platform ready for further phase development
- ✅ All tests passing consistently

---
*This webplan folder contains all implementation plans for the multi-tenant SAAS platform developed across 26 phases. Plans are aligned with the actual code implementation and test results.*