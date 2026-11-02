# Phase 0 — Module Restructure Plan

## Objective
Split the flat module layout into bounded-context modules with clear ownership, import-linter rules, and per-module test directories. This must be done BEFORE any M1/M2 code exists in the old layout.

## Non-Negotiable Requirements
- [ ] `modules/<bounded_context>/` split with table ownership map
- [ ] Import-linter installed and green, 3 contracts, 0 broken
- [ ] Per-module test directories exist BEFORE M1/M2 code
- [ ] Old layout must NOT be touched until restructure is complete
- [ ] DNS wildcard task opened (Phase 0 blocker)

## Exit Criteria
- [ ] Git log shows restructure preceded M1
- [ ] Phase 0 sign-off recorded (02/03/04/05)
- [ ] CI green on new module structure
- [ ] Import-linter: 3 contracts, 0 broken

## Key Deliverables
1. **Module ownership map** — Which bounded context owns which table(s)
2. **Import-linter configuration** — 3 contracts enforced
3. **Per-module test directories** — `tests/<module>/` for each context
4. **Old layout preservation** — Restructure happened first, no rework

## Technical Details
- **Duration**: 2 weeks (critical path)
- **Exit**: Sign-off on 02/03/04/05 recorded
- **Dependencies**: None (must come FIRST)

## Verification Commands
```bash
# Import-linter green
venv\Scripts\python.exe -m ruff check app tests alembic\env.py

# Structural boundary tests
venv\Scripts\python.exe -m pytest tests tests/structure -q --no-header

# Verify module structure
ls backend/app/modules/
```

---
*This plan is the FOUNDATION. Do not start M1/M2 on the flat layout — restructure FIRST.*