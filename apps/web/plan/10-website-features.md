# Website Plan — Features

## Overview
Comprehensive feature list for the multi-tenant restaurant management platform. Covers all features across all tiers, with implementation status and dependencies.

## Core Features (All Tiers)

### Authentication & Authorization
- **Email/Password Login**: Standard authentication flow
- **JWT Token Management**: Access + refresh tokens with tenant claims
- **Role-Based Access Control**: Owner, Manager, Waiter, Kitchen, Cashier roles
- **Multi-Factor Authentication**: Optional email-based MFA
- **Password Reset**: Secure token-based reset flow
- **Account Lockout**: 5 failed attempts → 30-minute lockout
- **Session Management**: 15-minute idle, 24-hour max session

### Table Management
- **Create Tables**: Add tables with code, name, capacity, branch
- **Edit Tables**: Update table details, capacity, status
- **Archive/Restore**: Soft delete and restore tables
- **Table Status**: Active, occupied, archived
- **Table Visualization**: Grid view with status indicators
- **Branch Assignment**: Assign tables to specific branches
- **QR Code Generation**: Generate QR codes for each table

### QR Ordering (Customer-Facing)
- **QR Code Scanning**: Scan QR to access menu
- **Menu Display**: Category-based menu with images/prices
- **Shopping Cart**: Add/remove items, quantity selection
- **Order Submission**: Submit order with customer note
- **Order Status Tracking**: Real-time order status updates
- **Bill Viewing**: View bill details and payment status
- **Rate Order**: Submit rating and comment

### Order Management
- **Order Creation**: From QR or waiter
- **Order Status**: Pending, accepted, rejected, cancelled, completed
- **Order Items**: Item name, quantity, price, tax, total
- **Customer Notes**: Special instructions
- **Idempotency**: Prevent duplicate submissions
- **Order History**: View past orders per table

### Kitchen Display
- **Order Queue**: View pending/accepted orders
- **Order Status Updates**: Accept/reject/cancel/complete
- **Kitchen Tickets**: Ticket items with status
- **Real-time Updates**: WebSocket-based updates (future)
- **Kitchen Timing**: Track preparation time

### Cashier Operations
- **Bill Generation**: Generate bill from dining session
- **Payment Processing**: Record payments (cash, card, etc.)
- **Balance Tracking**: Track paid vs. balance due
- **Receipt Generation**: Print/email receipts
- **Payment History**: View all payments per bill

### Dining Session Management
- **Session Opening**: Open session for table
- **Session Closing**: Close session, generate bill
- **Session Tracking**: Track session duration, orders
- **Session Analytics**: Session-level metrics

### Menu Management
- **Menu Items**: Create, edit, delete menu items
- **Categories**: Organize items by category
- **Pricing**: Set prices per item
- **Availability**: Mark items as available/unavailable
- **Images**: Upload item images
- **Modifiers**: Add/remove modifiers (future)

### Inventory Management (Future)
- **Stock Tracking**: Track ingredient stock levels
- **Low Stock Alerts**: Notifications for low stock
- **Supplier Management**: Track suppliers and orders
- **Purchase Orders**: Create and manage purchase orders

## Professional Tier Features

### Multi-Branch Management
- **Branch Creation**: Add new branches
- **Branch Editing**: Update branch details, hours, settings
- **Branch Status**: Active, suspended, deleted
- **Branch Analytics**: Per-branch performance metrics
- **Branch Transfer**: Transfer tables between branches

### Subdomain Configuration
- **Subdomain Setup**: Configure `{tenant}.platform.com`
- **Hostname Validation**: Verify subdomain ownership
- **DNS Management**: DNS record management
- **SSL Certificates**: Automated SSL for subdomains

### Audit Viewer
- **Audit Trail**: Full activity log (who, what, when)
- **Filtering**: By user, action, date, status
- **Export**: CSV, JSON, PDF export
- **Retention**: 90-day minimum retention
- **Search**: Full-text search across logs

### Suspend/Reactivate
- **Tenant Suspension**: Suspend tenant (D10 gate)
- **Tenant Reactivation**: Reactivate suspended tenant
- **Suspension Reasons**: Track reason for suspension
- **Notification**: Email notification on suspend/reactivate
- **Data Retention**: Data preserved during suspension

### Advanced Analytics
- **Revenue Reports**: Revenue by branch, day, hour
- **Order Analytics**: Order count, average order value, peak hours
- **Occupancy Analytics**: Table occupancy rates, turnover
- **QR Scan Stats**: QR code scan counts, conversion rates
- **Customer Analytics**: Customer demographics, ordering patterns
- **Custom Date Ranges**: Flexible date range selection

### API Access
- **REST API**: Full API access for integrations
- **API Documentation**: Interactive API docs
- **API Keys**: Secure API key management
- **Rate Limiting**: Configurable rate limits
- **Webhooks**: Event-driven integrations

### Custom Branding
- **Logo Upload**: Upload primary and secondary logos
- **Color Scheme**: Customize primary/secondary colors
- **Custom Domain**: Map custom domain (e.g., `restaurant.domain.com`)
- **Email Templates**: Branded transactional emails

## Enterprise Tier Features

### Unlimited Branches
- **No Limit**: Unlimited branches per tenant
- **Branch Hierarchy**: Parent/child branch relationships
- **Branch-Based Permissions**: Granular access control per branch
- **Branch Analytics**: Per-branch performance metrics
- **Branch Transfer**: Transfer tables/customers between branches

### White-Label Solution
- **Remove Platform Branding**: Full white-label
- **Custom Logos**: Upload primary/secondary logos
- **Color Schemes**: Full color palette customization
- **Custom Domains**: `restaurant.domain.com`
- **Email Templates**: Branded transactional emails
- **Login Page**: Fully branded authentication pages

### Advanced API Access
- **Full REST API**: Complete access to all endpoints
- **Webhook Subscriptions**: Real-time event notifications
- **API Rate Limits**: 500 calls/minute (configurable)
- **API Versioning**: v1, v2 endpoints with backward compatibility
- **Developer Portal**: Interactive API docs, test console
- **SDKs**: JavaScript/TypeScript, Python, PHP, .NET

### Priority Support
- **Dedicated Account Manager**: Single point of contact
- **24/7 Support**: Phone, email, chat support
- **SLA**: 2-hour response time for critical issues
- **Quarterly Business Reviews**: Quarterly performance reviews
- **Training Sessions**: On-demand and scheduled training

### Advanced Analytics
- **Predictive Analytics**: AI-powered demand forecasting
- **A/B Testing**: Feature experimentation framework
- **Cohort Analysis**: Customer retention and lifetime value
- **Custom Reports**: Ad-hoc reporting builder
- **Data Export**: CSV, JSON, PDF, Excel export

### Compliance & Security
- **SOC 2 Type II**: Compliance framework (future)
- **Data Residency**: EU, US, APAC data centers
- **SSO Integration**: SAML, OAuth2, OpenID Connect
- **Audit Logs Retention**: 2 years minimum
- **Compliance Reports**: SOC 2, GDPR, CCPA reports

### Enterprise Dashboard
- **Executive Summary**: Key metrics, revenue, branches
- **Branch Performance**: Per-branch analytics
- **Revenue Charts**: Interactive revenue visualization
- **Compliance Reports**: SOC 2, GDPR, CCPA reports
- **User Management**: Admin console for user management

### SSO Configuration
- **SAML 2.0**: Enterprise SSO via SAML
- **OAuth2**: OAuth2/OIDC integration
- **Identity Providers**: Okta, Azure AD, Google Workspace
- **Test Connection**: Validate SSO configuration
- **Certificate Management**: X.509 certificate handling

### Custom Branding Studio
- **Logo Upload**: Drag-and-drop logo upload
- **Color Scheme Editor**: Visual color picker
- **Domain Configuration**: Custom domain setup
- **Preview**: Real-time preview of branding
- **Export**: Export branding configuration

## Feature Gating Model

### Entitlement-Based Gating (Master Plan Approach)
Features are gated by entitlements, not by page availability:
- Server-side only, checked at mutation time
- `check-before-create` pattern
- Feature flags in `plans` table: `branches.limit`, `staff_users.limit`, `orders_per_month.limit`, `online_payments.enabled`, `inventory.enabled`, `custom_reports.enabled`, `api_access.enabled`, `qr_sessions_per_day.limit`

### Entitlement Configuration
```json
{
  "branches": { "limit": 1 },
  "staff_users": { "limit": 10 },
  "orders_per_month": { "limit": 5000 },
  "online_payments": { "enabled": false },
  "inventory": { "enabled": false },
  "custom_reports": { "enabled": false },
  "api_access": { "enabled": false },
  "qr_sessions_per_day": { "limit": 2000 }
}
```

### Tier Mapping
| Feature | Basic | Professional | Enterprise |
|---------|-------|--------------|------------|
| `branches.limit` | 1 | 5 | Unlimited |
| `staff_users.limit` | 5 | 25 | Unlimited |
| `orders_per_month.limit` | 1000 | 10000 | Unlimited |
| `online_payments.enabled` | false | true | true |
| `inventory.enabled` | false | true | true |
| `custom_reports.enabled` | false | true | true |
| `api_access.enabled` | false | true | true |
| `qr_sessions_per_day.limit` | 100 | 1000 | Unlimited |

## Feature Implementation Status

### ✅ Implemented (Phases 0-5)
- Module restructure
- Tenant columns (tenant_id, permission_version)
- TenantContext middleware
- Memberships live-read
- JWT claims upgrade (tenant_id, refresh tokens)
- Branch model (branch_id on 5 tables)
- RLS policies + SET_LOCAL
- Thin super admin (realm, router, invoices, audit)
- Customer subdomain (in progress)

### ⏳ Pending
- Waiter request (Phase 8)
- Legacy drop (Phase 9)
- Advanced analytics (Phase 10)
- Mobile app (Phase 11)
- Marketplace (Phase 12)
- AI features (Phase 13)
- Enterprise integrations (Phase 14)
- Global expansion (Phase 15)

### ⏸️ Skipped
- Phase 6 (Optional Stripe) — per user request

## Verification
- ✅ 43/43 isolation/structure tests pass
- ✅ 15/15 table tests pass
- ✅ ruff: 0 errors
- ✅ import-linter: 0 broken
- ✅ Structural boundary tests pass
- ✅ No plan regression

---
*Feature plan aligned with 26-phase backend implementation. All features gated by entitlements, not page availability.*