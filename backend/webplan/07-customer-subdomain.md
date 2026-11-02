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
- [ ] Wildcard TLS live on `*.platform.com` ✅
- [ ] QR hostname cross-check implemented ✅
- [ ] Per-tenant branding configurable ✅
- [ ] No cross-tenant redirect (hostname validation enforced) ✅
- [ ] `{tenant}.platform.com/t/{token}` works ✅
- [ ] Wrong-hostname token fails safely ✅
- [ ] All 43/43 + 15/15 tests still pass ✅

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