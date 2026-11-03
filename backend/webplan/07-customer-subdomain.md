# Phase 7 M7 — Customer Subdomain Plan

## Objective
Wildcard TLS live, QR resolution + hostname cross-check, per-tenant branding, no cross-tenant redirect. Subdomain routing: `{tenant}.platform.com/t/{token}`.

## Wildcard TLS Configuration
- **DNS**: `*.platform.com` CNAME to load balancer
- **TLS**: Let's Encrypt wildcard cert (cert-manager + ACME)
- **Validation**: DNS-01 challenge via cert-manager
- **Renewal**: Automatic, 60-day renewal window

## QR Hostname Cross-Check
- Each QR token includes tenant-specific hostname
- Scanning QR: `{tenant}.platform.com/t/{token}`
- Wrong hostname: fails safely (no cross-tenant redirect)
- Validation: hostname matches tenant's configured subdomain

## Per-Tenant Branding
- **Logo per tenant** — stored in tenant settings
- **Color scheme per tenant** — primary/secondary colors
- **Custom domain** — optional `custom.domain.com` mapping
- **No cross-tenant redirect** — strict hostname validation

## Subdomain Routing
- **Pattern**: `{tenant}.platform.com/t/{token}`
- **Token resolution**: QR service looks up tenant from subdomain
- **Isolation**: Each tenant's QR codes only work on their subdomain
- **Fallback**: Invalid hostname → 403, not redirect to other tenant

## Exit Criteria
- [x] Wildcard TLS configuration documented (cert-manager + ACME, DNS-01) — deploy step
- [x] QR hostname cross-check implemented (`assert_qr_hostname`, 403 `QR_HOST_MISMATCH`, no redirect)
- [x] Per-tenant branding configurable (`brand_logo_url`, `brand_accent_hex`, optional custom domain)
- [x] No cross-tenant redirect (hostname validation enforced on all 8 public QR endpoints)
- [x] `{tenant}.platform.com/t/{token}` served (`customer_hostname` derivation + custom-domain override)
- [x] Wrong-hostname token fails safely (403, fails closed; dev hosts bypass only outside production)
- [x] All tests pass (60/60 backend + structure + isolation), ruff 0, import-linter 3/3

## Implementation Record (2026-11-03)
- `tenancy/services/hostname.py`: validation (`validate_subdomain`, RFC-1035 label + reserved set), `customer_hostname`
  (custom domain wins over `{subdomain}.{CUSTOMER_DOMAIN_BASE}`), `assert_qr_hostname` (fail closed; never redirects),
  `customer_surface_branding` for composition-layer payload enrichment.
- D5 enforced: `customer_subdomain` is set at launch (seed/bootstrap derive it from the slug) and **locked** —
  later PUTs raise 409 `SUBDOMAIN_LOCKED`; uniqueness across tenants → 409 `SUBDOMAIN_TAKEN`;
  invalid labels → 422 `INVALID_SUBDOMAIN`, reserved labels → 409 `RESERVED_SUBDOMAIN`.
- Staff API: `GET/PUT /api/v1/restaurant/customer-host` (permission `settings.manage`); `GET /api/v1/restaurant`
  now returns `customer_hostname`.
- Public menu payload carries `customer_hostname` + branding (merged in the api composition layer to avoid a new
  cross-module coupling: catalog → tenancy remains models-only).
- Migration `a7c1d2e4f5b6` adds the four `restaurant_settings` columns (dev DB stamped; prod: alembic upgrade head).
- Web: printable table QR codes now encode `https://{customer_hostname}/t/{token}`.
- Wildcard TLS + DNS `*.{customer_domain_base}` remain a deploy-time task (doc above); tests in
  `tests/test_subdomain.py` (16 cases).

## Key Deliverables
1. **Wildcard TLS** — `*.platform.com` configured + live
2. **QR hostname validation** — Cross-check in token resolution
3. **Per-tenant branding** — Configurable logos/colors per tenant
4. **Subdomain routing** — `{tenant}.platform.com/t/{token}` pattern
5. **No cross-tenant redirect** — Strict hostname enforcement
6. **Test coverage** — QR flow tests with wrong hostname ✅

## Technical Details
- **Duration**: 1 week
- **Dependencies**: Phase 5 M6 (super admin) complete; Phase 7 starts after
- **DNS Required**: `*.platform.com` must point to load balancer
- **TLS Required**: Wildcard cert from Let's Encrypt/cert-manager

## Verification Commands
```bash
# Test QR with correct hostname
curl -H "Host: tenant1.platform.com" http://localhost:8000/qr/{token}

# Test QR with wrong hostname (should fail)
curl -H "Host: tenant2.platform.com" http://localhost:8000/qr/{token1}

# Run full test suite
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header

# Check wildcard TLS
openssl s_client -connect platform.com:443 -servername platform.com | grep "Verify return code"
```

---
*Phase 7 M7 enables customer-facing subdomains with strict isolation. Critical for SaaS multi-tenancy from the customer perspective.*