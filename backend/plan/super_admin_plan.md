> **Product source, not an execution contract.** The controlled implementation plan is in `backend/plan/super_admin/00-README.md`. Sections here that `super_admin/12-spec-traceability.md` marks P2/P3 are deliberately deferred; they are not missing MVP work.

1. Super Admin dashboard




















12










The dashboard gives the platform owner an overview of the entire SaaS business.

Information displayed:
- Total registered restaurants.
- Active restaurants.
- Trial restaurants.
- Suspended restaurants.
- Cancelled subscriptions.
- Total branches.
- Total registered staff accounts.
- Total platform users.
- Active subscriptions.
- Monthly recurring revenue (MRR).
- Annual recurring revenue (ARR).
- Total subscription collections.
- Pending payments.
- Failed payments.
- Trial conversion rate.
- New restaurant registrations.
- Subscription renewal rate.
- Churn rate.
- Platform service health.
- Recent platform activities.
How it works:
1. Super Admin logs in.
2. Backend retrieves platform-wide aggregated information.
3. Dashboard displays metrics and charts.
4. Super Admin selects a date range to filter reports.
5. Clicking a metric opens its corresponding management page.
Important: MRR, ARR, collections and revenue must be calculated separately. A yearly subscription payment should not be treated as recurring monthly cash collection.
Planned
2. Restaurant / tenant management




















11










This is one of the most important Super Admin modules.

Every restaurant business registered on your platform is a tenant.

Restaurant list should display:
Field	Description
Restaurant ID	Unique tenant identifier
Restaurant name	Business name
Owner	Primary account owner
Email	Registered email
Phone	Contact number
Branches	Number of branches
Plan	Current subscription
Status	Active, trial, suspended
Created date	Registration date
Renewal date	Subscription renewal

Actions available:
- View restaurant details.
- Create restaurant manually.
- Edit business information.
- Verify restaurant.
- Approve or reject registration if approval is required.
- Activate tenant.
- Suspend tenant.
- Reactivate tenant.
- Archive tenant.
- View subscription.
- View branches.
- View staff accounts.
- View payment history.
- View usage statistics.
- View audit logs.
- Contact restaurant owner.
Detailed workflow:

Suppose a new restaurant registers.
1. Restaurant owner submits registration.
2. Backend creates a tenant and owner membership.
3. Restaurant enters trial or pending-verification status, according to your onboarding policy.
4. Super Admin sees the new registration.
5. Super Admin verifies business information if manual verification is enabled.
6. Restaurant receives access according to its subscription status.
7. Super Admin can suspend the tenant if a valid policy or security reason exists.
Critical security rule: Suspending one restaurant must not affect other restaurants. Tenant suspension must be enforced in the backend, not just by hiding the restaurant from the dashboard.
3. Subscription and plan management




















11










Super Admin controls the subscription products sold to restaurants.

A. Plan creation

Create different subscription plans, for example:
Plan	Example price	Intended customer
Starter	NPR 999/month	Small restaurant
Growth	NPR 1,999/month	Growing restaurant
Professional	NPR 3,999/month	Larger restaurant
Enterprise	Custom	Restaurant chains

These are proposed prices, not validated market prices.

B. Plan configuration

Each plan should have configurable limits and features:
- Monthly and yearly price.
- Maximum branches.
- Maximum staff accounts.
- Maximum tables.
- Maximum menu items.
- Maximum monthly orders (if you choose usage-based limits).
- Storage allowance.
- QR ordering availability.
- Kitchen display availability.
- Inventory management availability.
- Advanced reports availability.
- Multi-branch analytics.
- Customer loyalty features.
- Priority support.
- Custom domain availability.
- API access.
C. Plan actions
- Create plan.
- Edit plan.
- Duplicate plan.
- Activate/deactivate plan.
- Archive plan.
- Change price.
- Configure trial duration.
- Configure feature access.
- Configure usage limits.
How it works:
1. Super Admin creates the Growth plan.
2. Super Admin sets its price and limits.
3. Restaurant owner selects Growth.
4. Backend creates a subscription.
5. Subscription entitlement service grants the allowed features.
6. Every relevant API checks the restaurant's entitlement and usage.
7. If the restaurant exceeds a limit, the system applies the configured policy.
Do not scatter subscription checks throughout the application. Build one centralized entitlement service.
4. Subscription lifecycle management
This is different from creating plans. This module manages individual restaurant subscriptions.

Subscription statuses:
Status	Meaning
Trialing	Free trial in progress
Active	Subscription is valid
Past due	Payment overdue
Grace period	Temporary extra access
Suspended	Access restricted
Cancelled	Subscription cancelled
Expired	Subscription period ended

Features:
- View all subscriptions.
- Search by restaurant.
- Filter by plan and status.
- View start and end dates.
- View next billing date.
- View payment history.
- Extend a trial.
- Change subscription plan.
- Upgrade or downgrade.
- Apply discount.
- Apply promotional offer.
- Cancel subscription.
- Reactivate subscription.
- Suspend subscription.
- Grant temporary access.
- Configure grace period.
- View subscription change history.
Example workflow:

A restaurant has a Growth subscription ending on November 30.
1. The system sends renewal reminders.
2. The restaurant makes a payment.
3. The payment is verified.
4. Subscription expiry is extended.
5. Entitlements are recalculated.
6. An invoice or receipt is generated.
If payment fails, the system moves the subscription to past_due, retries according to the payment policy, and eventually applies the grace-period or suspension rules.

Important: Do not immediately delete restaurant data when a subscription expires. Restrict access according to policy and provide a clear data export and retention process.
5. Payment and transaction management




















10










This module manages money paid by restaurants to your SaaS company.

It is separate from restaurant customer payments. For example, when a customer pays a restaurant's bill through eSewa, that is the restaurant's transaction, not automatically your SaaS revenue.

Features:
- View all SaaS payments.
- Search transactions.
- Filter by date.
- Filter by restaurant.
- Filter by payment method.
- Filter by successful, pending and failed status.
- View transaction reference.
- View payment provider response.
- View subscription linked to payment.
- Record offline/manual payments.
- Verify manual payments.
- Handle refunds.
- Record payment adjustments.
- View payment reconciliation.
- Download transaction reports.
- View payment gateway fees.
Payment record should contain:
- Transaction ID.
- Tenant ID.
- Subscription ID.
- Amount.
- Currency.
- Payment method.
- Payment provider.
- Provider transaction reference.
- Payment status.
- Created date.
- Verified date.
- Refund information.
Example:

A restaurant pays NPR 1,999 for Growth.
1. Payment provider sends a transaction confirmation.
2. Backend verifies the transaction with the provider.
3. Backend records the payment.
4. Subscription is activated or renewed.
5. Restaurant receives confirmation.
6. Super Admin can see the transaction.
Never let the frontend directly mark a payment as successful. Verify it on the backend.
6. Invoice and financial management
Super Admin should be able to manage financial documents related to SaaS subscriptions.

Features:
- Automatically generate invoices.
- Generate manual invoices.
- Assign invoice numbers.
- View unpaid invoices.
- View paid invoices.
- View overdue invoices.
- Download PDF invoices.
- Send invoices by email.
- Apply discounts.
- Apply taxes.
- Issue credit notes.
- Record refunds.
- Manage invoice cancellation.
- View revenue by month.
- Export financial reports.
Invoice information:
- SaaS company details.
- Restaurant business details.
- Invoice number.
- Subscription plan.
- Billing period.
- Subtotal.
- Discount.
- Tax.
- Total amount.
- Payment status.
- Payment reference.
For Nepal, configure tax and invoice requirements according to applicable accounting and tax rules. Do not hardcode one tax rate into the system.
7. Branch management




















11










Super Admin needs a platform-wide view of restaurant branches.

Features:
- View all branches across all tenants.
- Search branches.
- Filter by restaurant.
- View branch information.
- View branch owner or manager.
- View branch address.
- View branch status.
- View branch creation date.
- View branch subscription entitlement.
- Activate or deactivate a branch.
- Investigate branch-level issues.
- View branch usage statistics.
How it works:

If Restaurant A has three branches, the Super Admin can see all three under Restaurant A.

The restaurant owner manages their branch details and daily operations. Super Admin has platform-level oversight and exceptional administrative controls.
8. User and staff management




















10










This module manages user accounts across the platform.

Features:
- View all registered users.
- Search users by email, phone or name.
- View account status.
- View user membership.
- View associated restaurants.
- View branch access.
- View assigned roles.
- Disable an account.
- Reactivate an account.
- Revoke sessions.
- Force password reset through a secure recovery workflow.
- Investigate suspicious login activity.
- View user activity logs.
Roles should be separated:
- Platform Super Admin.
- Platform Support Agent.
- Platform Finance Admin.
- Restaurant Owner.
- Restaurant Manager.
- Cashier.
- Waiter.
- Kitchen Staff.
- Inventory Manager.
Super Admin should not casually edit restaurant staff permissions. The restaurant owner or authorized manager should normally manage their own team.
9. Support and complaint management




















10










Restaurants will need help when they face problems. Super Admin should have a built-in support system.

Features:
- View support tickets.
- Create tickets on behalf of restaurants.
- Assign tickets to support staff.
- Set priority.
- Categorize issues.
- Add internal notes.
- Communicate with restaurant owners.
- Attach screenshots and documents.
- Track ticket status.
- Set response and resolution targets.
- Escalate serious issues.
- View ticket history.
- Collect customer satisfaction ratings.
Ticket statuses:

Open → Assigned → In Progress → Waiting for Customer → Resolved → Closed

Example:

A restaurant reports that its QR ordering is not working.
1. Restaurant creates a support ticket.
2. Super Admin sees the issue.
3. Support agent checks restaurant and branch details.
4. Agent reviews relevant logs.
5. Agent identifies the issue.
6. Agent responds and resolves the ticket.
7. Restaurant receives a notification.
10. Platform notifications and announcements
Super Admin should control communications sent to restaurants.

Features:
- Send announcements to all restaurants.
- Send announcements to selected restaurants.
- Send notifications to a particular tenant.
- Send maintenance notifications.
- Send subscription renewal reminders.
- Send payment failure notifications.
- Send new feature announcements.
- Send security alerts.
- Schedule notifications.
- Manage email templates.
- Manage push notification templates.
- View delivery status.
Example:

You release a new inventory module.

You can send an announcement to all restaurants:

"Inventory Management is now available. You can track ingredients, stock levels and purchases from your dashboard."

Support targeting by subscription plan, branch count or enabled feature.
11. Platform configuration and settings
This module controls global application behavior.

General settings:
- SaaS company name.
- Company logo.
- Company address.
- Contact email.
- Support phone.
- Default currency.
- Supported currencies.
- Default timezone.
- Date and time formats.
- Supported languages.
- Default tax configuration where applicable.
Platform settings:
- Registration enabled/disabled.
- Email verification requirement.
- Phone verification requirement.
- Manual restaurant approval.
- Default trial duration.
- Default subscription grace period.
- Allowed file types.
- Maximum upload size.
- Password policy.
- Session expiration policy.
- Maintenance mode.
Important: Platform defaults should not unexpectedly overwrite restaurant-specific settings. Use explicit tenant-level overrides where necessary.
12. Platform analytics and reports




















8










Super Admin needs reports to understand whether the SaaS business is growing.

Business reports:
- Total registered restaurants.
- New tenant registrations.
- Active tenant growth.
- Monthly recurring revenue.
- Annual recurring revenue.
- Revenue collected.
- Outstanding subscription payments.
- Refunds.
- Failed transactions.
- Subscription upgrades.
- Subscription downgrades.
- Trial-to-paid conversion.
- Customer churn.
- Revenue by subscription plan.
- Revenue by month.
- Revenue by payment method.
- Average revenue per tenant.
- Subscription renewal rate.
Usage reports:
- Number of branches.
- Number of active staff.
- Number of orders processed.
- Number of QR codes generated.
- Storage consumed.
- API requests.
- Feature adoption.
- Usage by subscription plan.
Useful reporting filters:
- Date range.
- Restaurant.
- Branch.
- Subscription plan.
- Subscription status.
- Payment status.
13. Platform audit logs







clouisle.asia


This is essential for accountability and security.

Every important administrative action should be recorded.

Audit events:
- Super Admin login.
- Failed login.
- Restaurant created.
- Restaurant suspended.
- Subscription changed.
- Plan price changed.
- Payment manually verified.
- Refund issued.
- User disabled.
- Branch deactivated.
- Support access granted.
- Restaurant data exported.
- Platform setting changed.
Each audit record should contain:
Field	Purpose
Actor ID	Who performed the action
Action	What happened
Target type	Tenant, user, subscription, etc.
Target ID	Which resource was affected
Timestamp	When it happened
IP address	Request origin
Metadata	Relevant change details
Reason	Why the action was taken

Audit logs should be append-only for normal application roles. Super Admins should not be able to silently rewrite or delete the history.
14. Security and access management
Super Admin has powerful access, so the panel needs stronger protection than ordinary restaurant accounts.

Features:
- Secure Super Admin authentication.
- Mandatory multi-factor authentication.
- Role-based platform permissions.
- Session management.
- Login history.
- Active session revocation.
- Failed login detection.
- Rate limiting.
- Suspicious activity alerts.
- IP restrictions (optional).
- Security event logs.
- Sensitive action confirmation.
- Re-authentication for high-risk operations.
- Administrative access expiry.
Recommended Super Admin roles:
Platform role	Permissions
Super Admin	Full platform control
Operations Admin	Tenant and branch operations
Finance Admin	Plans, invoices and payments
Support Agent	Tickets and limited tenant diagnostics
Security Admin	Security events and access control

Do not give every employee full Super Admin privileges.
15. Tenant diagnostics and support access
This is a particularly useful feature for a SaaS product.

When a restaurant reports a problem, Super Admin should be able to inspect the technical and operational health of that tenant.

Features:
- View tenant configuration.
- View branch configuration.
- View recent API errors.
- View recent failed jobs.
- View subscription entitlement status.
- View usage and limit consumption.
- View integration status.
- View recent login activity.
- View notification delivery status.
- View relevant audit events.
- View database-related diagnostic information without exposing other tenants' data.
Optional: controlled support access

You may add a feature called "Support Access" or "View as Restaurant".

How it should work:
1. Support agent requests access.
2. System requires a reason.
3. An authorized admin approves it if necessary.
4. Access is limited to one tenant.
5. Access expires automatically.
6. All actions are audited.
7. Sensitive operations remain restricted.
I would avoid an unrestricted "Login as Owner" feature. It creates a major security and accountability risk. Prefer read-only diagnostics first, with narrowly scoped, audited actions where needed.
16. System health and monitoring




















10










Super Admin should be able to monitor the technical health of the SaaS.

Features:
- API availability.
- API response time.
- Error rate.
- Request volume.
- Database health.
- Database connection usage.
- Redis health.
- Celery worker status.
- Background task failures.
- Storage usage.
- File upload errors.
- Payment gateway status.
- Email delivery status.
- Push notification status.
- Scheduled job status.
- Service uptime.
- Incident history.
Example workflow:

If Redis becomes unavailable:
1. Monitoring detects a failed health check.
2. An alert is generated.
3. Super Admin sees Redis as unhealthy.
4. The technical team investigates.
5. Once recovered, the system records the incident and recovery time.
Do not make the Super Admin dashboard a replacement for professional observability tools. Integrate with monitoring systems and show their relevant metrics.
17. Integration management
Restaurants may use different services. Super Admin needs to manage the integrations supported by your platform.

Integrations to manage:
- eSewa.
- Khalti.
- Fonepay.
- Bank payment integrations.
- Email providers.
- SMS providers.
- Push notification providers.
- Google Maps.
- Google Business Profile.
- Cloud storage.
- Analytics services.
- Accounting integrations (future).
Features:
- Enable or disable an integration globally.
- Configure provider credentials securely.
- View integration health.
- View failed integration requests.
- View webhook delivery history.
- Retry failed webhooks where safe.
- Configure supported payment methods.
- View integration usage.
- Configure test and production environments.
Important architecture decision: Global integration configuration should be separate from tenant configuration. For example, the platform may support eSewa, but each restaurant must configure its own merchant credentials if the integration requires restaurant-specific payment accounts.

Never display full API secrets in the admin interface after they have been saved.
18. Feature flags and product rollout







featbit.co


This allows you to release new functionality without enabling it for everyone immediately.

Features:
- Enable or disable a feature globally.
- Enable a feature for selected tenants.
- Enable a feature for a particular subscription plan.
- Gradually release a feature.
- Configure rollout percentages.
- Disable a feature during an incident.
- Schedule feature activation.
- View feature adoption.
Example:

You develop inventory management.
1. Enable it for your internal test tenant.
2. Test it with two pilot restaurants.
3. Fix issues.
4. Enable it for Professional subscribers.
5. Make it generally available after testing.
Use feature flags for controlled releases, but keep subscription entitlements as the authority for what a tenant has purchased. A feature flag and a paid entitlement solve different problems.
19. Restaurant onboarding management







dribbble.com


Super Admin should be able to monitor whether new restaurants successfully set up the platform.

Features:
- View newly registered restaurants.
- View onboarding progress.
- Track owner profile completion.
- Track restaurant information completion.
- Track first branch creation.
- Track menu creation.
- Track table creation.
- Track QR generation.
- Track first order.
- Assign onboarding support.
- Send onboarding reminders.
- Schedule onboarding demonstrations.
- Mark onboarding as completed.
Example onboarding checklist:
1. Create restaurant account.
2. Verify email and phone.
3. Enter business details.
4. Create first branch.
5. Add menu categories.
6. Add food items.
7. Create tables.
8. Generate table QR codes.
9. Invite staff.
10. Complete first test order.
The dashboard can highlight restaurants that registered but never completed setup. This helps reduce trial abandonment.
20. Promotions, discounts and coupon management
Super Admin should be able to manage offers used to acquire and retain SaaS customers.

Features:
- Create coupon codes.
- Set fixed-amount discounts.
- Set percentage discounts.
- Set coupon expiration.
- Limit coupon usage.
- Restrict coupons to selected plans.
- Restrict coupons to new customers.
- Create referral promotions.
- Create seasonal offers.
- Create promotional campaigns.
- View coupon usage.
- View discount costs.
- Deactivate coupons.
Example:

WELCOME20
- 20% off.
- First subscription only.
- Valid for 30 days.
- Applicable to Starter and Growth plans.
Discounts must be calculated and validated by the backend, not trusted from the browser.
21. Platform content and CMS management
Super Admin should control the public-facing SaaS website and customer communication content.

Features:
- Manage homepage content.
- Manage product feature descriptions.
- Manage pricing page content.
- Manage FAQ.
- Manage testimonials.
- Manage blog posts.
- Manage announcements.
- Manage terms and conditions.
- Manage privacy policy.
- Manage help documentation.
- Manage contact information.
- Upload platform logo and images.
- Configure SEO title and description.
- Publish and unpublish content.
This allows you to update your marketing website without modifying application code for every small content change.
22. API and developer management
This becomes useful when you eventually allow restaurant chains or external developers to integrate with your SaaS.

Features:
- Manage API clients.
- Issue API credentials.
- Revoke credentials.
- Configure API scopes.
- Set rate limits.
- View API usage.
- View API error logs.
- Manage webhook endpoints.
- View webhook delivery attempts.
- Retry failed webhook deliveries.
- Provide API documentation.
- Configure API version support.
API keys should be scoped, revocable, securely stored and associated with the correct tenant. Never issue unrestricted platform-level credentials to a restaurant.
23. Data management, backups and retention







continuity.datto.com


This module protects the data of every restaurant using your system.

Features:
- View backup status.
- Monitor backup schedules.
- Monitor backup failures.
- View database storage usage.
- Track tenant data consumption.
- Manage file storage.
- Manage data retention policies.
- Handle tenant data export requests.
- Handle tenant deletion requests.
- Track data deletion jobs.
- Monitor restore tests.
- Maintain disaster recovery documentation.
Critical distinction: A successful database backup does not prove that recovery works. You need periodic restore testing.

For a shared database, a tenant data export must include only that tenant's data, including its branches, orders, users' tenant memberships, payment records and related files.
24. Incident and maintenance management
Features:
- Create system incidents.
- Assign incident severity.
- Record incident descriptions.
- Assign technical responders.
- Track investigation progress.
- Publish maintenance notices.
- Schedule maintenance windows.
- Enable maintenance mode.
- Notify affected tenants.
- Record resolution details.
- Maintain post-incident reports.
Example severity levels:
Severity	Example
Critical	All restaurants cannot access the system
High	Orders cannot reach the kitchen
Medium	Payment integration is unavailable
Low	A report page is loading slowly

Maintenance mode should be configurable. Ideally, you can restrict new registrations or selected operations without unnecessarily blocking every restaurant.
25. Legal, compliance and privacy management
Features:
- Manage platform terms and conditions.
- Manage privacy policy.
- Manage subscription agreements.
- Record terms acceptance.
- Track consent versions.
- Manage data access requests.
- Manage data correction requests.
- Manage data export requests.
- Manage deletion requests.
- Track data retention.
- Maintain security incident records.
- Record administrative data access.
For a Nepal-based SaaS, have the platform's legal and tax requirements reviewed against applicable Nepalese laws and regulations. The software should support policy changes rather than hardcoding legal assumptions.
26. Super Admin profile and personal settings
- View profile.
- Change profile information.
- Change password.
- Configure MFA.
- View login history.
- Manage active sessions.
- Revoke sessions.
- Configure notification preferences.
- Configure dashboard preferences.
- View assigned platform role.
- Request additional permissions.

27. Super Admin navigation structure
I recommend organizing the sidebar into logical sections instead of showing 25 unrelated menu items.
REST PLATFORM — SUPER ADMIN


OVERVIEW
- Dashboard
- Platform Analytics
- System Health
  BUSINESS MANAGEMENT
- Restaurants / Tenants
- Branches
- Users & Staff
- Onboarding
  SUBSCRIPTIONS & FINANCE
- Plans & Pricing
- Subscriptions
- Transactions
- Invoices
- Coupons & Promotions
  CUSTOMER SUCCESS
- Support Tickets
- Announcements
- Notifications
  PLATFORM MANAGEMENT
- Feature Flags
- Integrations
- API Management
- Website CMS
  SECURITY & INFRASTRUCTURE
- Audit Logs
- Security
- System Monitoring
- Backups & Data
- Incidents & Maintenance
  CONFIGURATION
- General Settings
- Legal & Privacy
- Admin Users & Roles
- My Profile

28. Important Super Admin workflows
A feature list is not enough. Your system should support these complete workflows.
Workflow A: New restaurant registration
#chatgpt-mermaid-_r_2fg_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(13, 13, 13);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_2fg_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_2fg_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_2fg_ .error-icon{fill:rgb(243, 243, 243);}#chatgpt-mermaid-_r_2fg_ .error-text{fill:rgb(13, 13, 13);stroke:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fg_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_2fg_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_2fg_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_2fg_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_2fg_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_2fg_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_2fg_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fg_ .marker.cross{stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fg_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_2fg_ p{margin:0;}#chatgpt-mermaid-_r_2fg_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fg_ .cluster-label text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fg_ .cluster-label span{color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fg_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_2fg_ .label text,#chatgpt-mermaid-_r_2fg_ span{fill:rgb(13, 13, 13);color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fg_ .node rect,#chatgpt-mermaid-_r_2fg_ .node circle,#chatgpt-mermaid-_r_2fg_ .node ellipse,#chatgpt-mermaid-_r_2fg_ .node polygon,#chatgpt-mermaid-_r_2fg_ .node path{fill:rgb(222, 234, 251);stroke:rgb(83, 154, 248);stroke-width:1px;}#chatgpt-mermaid-_r_2fg_ .rough-node .label text,#chatgpt-mermaid-_r_2fg_ .node .label text,#chatgpt-mermaid-_r_2fg_ .image-shape .label,#chatgpt-mermaid-_r_2fg_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_2fg_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_2fg_ .rough-node .label,#chatgpt-mermaid-_r_2fg_ .node .label,#chatgpt-mermaid-_r_2fg_ .image-shape .label,#chatgpt-mermaid-_r_2fg_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_2fg_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_2fg_ .root .anchor path{fill:rgb(143, 143, 143)!important;stroke-width:0;stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fg_ .arrowheadPath{fill:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fg_ .edgePath .path{stroke:rgb(143, 143, 143);stroke-width:1px;}#chatgpt-mermaid-_r_2fg_ .flowchart-link{stroke:rgb(143, 143, 143);fill:none;}#chatgpt-mermaid-_r_2fg_ .edgeLabel{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-_r_2fg_ .edgeLabel p{background-color:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fg_ .edgeLabel rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fg_ .labelBkg{background-color:rgba(252, 252, 252, 0.5);}#chatgpt-mermaid-_r_2fg_ .cluster rect{fill:rgb(243, 243, 243);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_2fg_ .cluster text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fg_ .cluster span{color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fg_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(243, 243, 243);border:1px solid rgba(0, 0, 0, 0.1);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_2fg_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fg_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_2fg_ .icon-shape,#chatgpt-mermaid-_r_2fg_ .image-shape{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-_r_2fg_ .icon-shape p,#chatgpt-mermaid-_r_2fg_ .image-shape p{background-color:rgb(252, 252, 252);padding:2px;}#chatgpt-mermaid-_r_2fg_ .icon-shape .label rect,#chatgpt-mermaid-_r_2fg_ .image-shape .label rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fg_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_2fg_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_2fg_ .node .neo-node{stroke:rgb(83, 154, 248);}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_2fg_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_2fg_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_2fg_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_2fg_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].node .neo-line path{stroke:rgb(83, 154, 248);filter:none;}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_2fg_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_2fg_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fg_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_2fg_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fg_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(0, 79, 153);}#chatgpt-mermaid-_r_2fg_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(0, 79, 153);}#chatgpt-mermaid-_r_2fg_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_2fg_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_2fg_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-width:1px;}#chatgpt-mermaid-_r_2fg_ .node rect,#chatgpt-mermaid-_r_2fg_ .node circle,#chatgpt-mermaid-_r_2fg_ .node ellipse,#chatgpt-mermaid-_r_2fg_ .node polygon,#chatgpt-mermaid-_r_2fg_ .node path{fill:rgb(229, 243, 255);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_2fg_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_2fg_ .mermaid-decision .label-container{fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_2fg_ .edgePaths .flowchart-link{stroke:rgb(143, 143, 143);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_2fg_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fg_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Restaurant registersCreate tenantCreate owner membershipVerify email and phoneApproval required?Super Admin reviewsStart trialApproved?Reject with reasonAssign plan entitlementsRestaurant starts onboardingYesNoYesNo





Workflow B: Subscription payment and renewal
#chatgpt-mermaid-_r_2fn_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(13, 13, 13);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_2fn_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_2fn_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_2fn_ .error-icon{fill:rgb(243, 243, 243);}#chatgpt-mermaid-_r_2fn_ .error-text{fill:rgb(13, 13, 13);stroke:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fn_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_2fn_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_2fn_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_2fn_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_2fn_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_2fn_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_2fn_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fn_ .marker.cross{stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fn_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_2fn_ p{margin:0;}#chatgpt-mermaid-_r_2fn_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fn_ .cluster-label text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fn_ .cluster-label span{color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fn_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_2fn_ .label text,#chatgpt-mermaid-_r_2fn_ span{fill:rgb(13, 13, 13);color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fn_ .node rect,#chatgpt-mermaid-_r_2fn_ .node circle,#chatgpt-mermaid-_r_2fn_ .node ellipse,#chatgpt-mermaid-_r_2fn_ .node polygon,#chatgpt-mermaid-_r_2fn_ .node path{fill:rgb(222, 234, 251);stroke:rgb(83, 154, 248);stroke-width:1px;}#chatgpt-mermaid-_r_2fn_ .rough-node .label text,#chatgpt-mermaid-_r_2fn_ .node .label text,#chatgpt-mermaid-_r_2fn_ .image-shape .label,#chatgpt-mermaid-_r_2fn_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_2fn_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_2fn_ .rough-node .label,#chatgpt-mermaid-_r_2fn_ .node .label,#chatgpt-mermaid-_r_2fn_ .image-shape .label,#chatgpt-mermaid-_r_2fn_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_2fn_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_2fn_ .root .anchor path{fill:rgb(143, 143, 143)!important;stroke-width:0;stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fn_ .arrowheadPath{fill:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fn_ .edgePath .path{stroke:rgb(143, 143, 143);stroke-width:1px;}#chatgpt-mermaid-_r_2fn_ .flowchart-link{stroke:rgb(143, 143, 143);fill:none;}#chatgpt-mermaid-_r_2fn_ .edgeLabel{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-_r_2fn_ .edgeLabel p{background-color:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fn_ .edgeLabel rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fn_ .labelBkg{background-color:rgba(252, 252, 252, 0.5);}#chatgpt-mermaid-_r_2fn_ .cluster rect{fill:rgb(243, 243, 243);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_2fn_ .cluster text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fn_ .cluster span{color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fn_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(243, 243, 243);border:1px solid rgba(0, 0, 0, 0.1);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_2fn_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fn_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_2fn_ .icon-shape,#chatgpt-mermaid-_r_2fn_ .image-shape{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-_r_2fn_ .icon-shape p,#chatgpt-mermaid-_r_2fn_ .image-shape p{background-color:rgb(252, 252, 252);padding:2px;}#chatgpt-mermaid-_r_2fn_ .icon-shape .label rect,#chatgpt-mermaid-_r_2fn_ .image-shape .label rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fn_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_2fn_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_2fn_ .node .neo-node{stroke:rgb(83, 154, 248);}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_2fn_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_2fn_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_2fn_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_2fn_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].node .neo-line path{stroke:rgb(83, 154, 248);filter:none;}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_2fn_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_2fn_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fn_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_2fn_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fn_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(0, 79, 153);}#chatgpt-mermaid-_r_2fn_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(0, 79, 153);}#chatgpt-mermaid-_r_2fn_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_2fn_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_2fn_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-width:1px;}#chatgpt-mermaid-_r_2fn_ .node rect,#chatgpt-mermaid-_r_2fn_ .node circle,#chatgpt-mermaid-_r_2fn_ .node ellipse,#chatgpt-mermaid-_r_2fn_ .node polygon,#chatgpt-mermaid-_r_2fn_ .node path{fill:rgb(229, 243, 255);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_2fn_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_2fn_ .mermaid-decision .label-container{fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_2fn_ .edgePaths .flowchart-link{stroke:rgb(143, 143, 143);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_2fn_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fn_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Subscription renewal dueNotify restaurantRestaurant paysVerify provider transactionPayment successful?Record transactionGenerate invoiceExtend subscriptionUpdate entitlementsMark past dueRetry or grace periodRestrict access if policyrequiresYesNo





Workflow C: Restaurant suspension
#chatgpt-mermaid-_r_2fv_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(13, 13, 13);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_2fv_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_2fv_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_2fv_ .error-icon{fill:rgb(243, 243, 243);}#chatgpt-mermaid-_r_2fv_ .error-text{fill:rgb(13, 13, 13);stroke:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fv_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_2fv_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_2fv_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_2fv_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_2fv_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_2fv_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_2fv_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fv_ .marker.cross{stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fv_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_2fv_ p{margin:0;}#chatgpt-mermaid-_r_2fv_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fv_ .cluster-label text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fv_ .cluster-label span{color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fv_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_2fv_ .label text,#chatgpt-mermaid-_r_2fv_ span{fill:rgb(13, 13, 13);color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fv_ .node rect,#chatgpt-mermaid-_r_2fv_ .node circle,#chatgpt-mermaid-_r_2fv_ .node ellipse,#chatgpt-mermaid-_r_2fv_ .node polygon,#chatgpt-mermaid-_r_2fv_ .node path{fill:rgb(222, 234, 251);stroke:rgb(83, 154, 248);stroke-width:1px;}#chatgpt-mermaid-_r_2fv_ .rough-node .label text,#chatgpt-mermaid-_r_2fv_ .node .label text,#chatgpt-mermaid-_r_2fv_ .image-shape .label,#chatgpt-mermaid-_r_2fv_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_2fv_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_2fv_ .rough-node .label,#chatgpt-mermaid-_r_2fv_ .node .label,#chatgpt-mermaid-_r_2fv_ .image-shape .label,#chatgpt-mermaid-_r_2fv_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_2fv_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_2fv_ .root .anchor path{fill:rgb(143, 143, 143)!important;stroke-width:0;stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fv_ .arrowheadPath{fill:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fv_ .edgePath .path{stroke:rgb(143, 143, 143);stroke-width:1px;}#chatgpt-mermaid-_r_2fv_ .flowchart-link{stroke:rgb(143, 143, 143);fill:none;}#chatgpt-mermaid-_r_2fv_ .edgeLabel{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-_r_2fv_ .edgeLabel p{background-color:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fv_ .edgeLabel rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fv_ .labelBkg{background-color:rgba(252, 252, 252, 0.5);}#chatgpt-mermaid-_r_2fv_ .cluster rect{fill:rgb(243, 243, 243);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_2fv_ .cluster text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fv_ .cluster span{color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fv_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(243, 243, 243);border:1px solid rgba(0, 0, 0, 0.1);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_2fv_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2fv_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_2fv_ .icon-shape,#chatgpt-mermaid-_r_2fv_ .image-shape{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-_r_2fv_ .icon-shape p,#chatgpt-mermaid-_r_2fv_ .image-shape p{background-color:rgb(252, 252, 252);padding:2px;}#chatgpt-mermaid-_r_2fv_ .icon-shape .label rect,#chatgpt-mermaid-_r_2fv_ .image-shape .label rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2fv_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_2fv_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_2fv_ .node .neo-node{stroke:rgb(83, 154, 248);}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_2fv_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_2fv_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_2fv_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_2fv_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].node .neo-line path{stroke:rgb(83, 154, 248);filter:none;}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_2fv_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_2fv_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fv_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_2fv_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2fv_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(0, 79, 153);}#chatgpt-mermaid-_r_2fv_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(0, 79, 153);}#chatgpt-mermaid-_r_2fv_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_2fv_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_2fv_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-width:1px;}#chatgpt-mermaid-_r_2fv_ .node rect,#chatgpt-mermaid-_r_2fv_ .node circle,#chatgpt-mermaid-_r_2fv_ .node ellipse,#chatgpt-mermaid-_r_2fv_ .node polygon,#chatgpt-mermaid-_r_2fv_ .node path{fill:rgb(229, 243, 255);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_2fv_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_2fv_ .mermaid-decision .label-container{fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_2fv_ .edgePaths .flowchart-link{stroke:rgb(143, 143, 143);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_2fv_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2fv_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Super Admin selects tenantSelect suspension reasonConfirm privileged actionRecord audit eventChange tenant statusBackend blocks restrictedaccessNotify restaurant ownerSuper Admin can reactivate





Workflow D: Support access
#chatgpt-mermaid-_r_2g6_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(13, 13, 13);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_2g6_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_2g6_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_2g6_ .error-icon{fill:rgb(243, 243, 243);}#chatgpt-mermaid-_r_2g6_ .error-text{fill:rgb(13, 13, 13);stroke:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2g6_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_2g6_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_2g6_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_2g6_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_2g6_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_2g6_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_2g6_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2g6_ .marker.cross{stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2g6_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_2g6_ p{margin:0;}#chatgpt-mermaid-_r_2g6_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2g6_ .cluster-label text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2g6_ .cluster-label span{color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2g6_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_2g6_ .label text,#chatgpt-mermaid-_r_2g6_ span{fill:rgb(13, 13, 13);color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2g6_ .node rect,#chatgpt-mermaid-_r_2g6_ .node circle,#chatgpt-mermaid-_r_2g6_ .node ellipse,#chatgpt-mermaid-_r_2g6_ .node polygon,#chatgpt-mermaid-_r_2g6_ .node path{fill:rgb(222, 234, 251);stroke:rgb(83, 154, 248);stroke-width:1px;}#chatgpt-mermaid-_r_2g6_ .rough-node .label text,#chatgpt-mermaid-_r_2g6_ .node .label text,#chatgpt-mermaid-_r_2g6_ .image-shape .label,#chatgpt-mermaid-_r_2g6_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_2g6_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_2g6_ .rough-node .label,#chatgpt-mermaid-_r_2g6_ .node .label,#chatgpt-mermaid-_r_2g6_ .image-shape .label,#chatgpt-mermaid-_r_2g6_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_2g6_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_2g6_ .root .anchor path{fill:rgb(143, 143, 143)!important;stroke-width:0;stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2g6_ .arrowheadPath{fill:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2g6_ .edgePath .path{stroke:rgb(143, 143, 143);stroke-width:1px;}#chatgpt-mermaid-_r_2g6_ .flowchart-link{stroke:rgb(143, 143, 143);fill:none;}#chatgpt-mermaid-_r_2g6_ .edgeLabel{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-_r_2g6_ .edgeLabel p{background-color:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2g6_ .edgeLabel rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2g6_ .labelBkg{background-color:rgba(252, 252, 252, 0.5);}#chatgpt-mermaid-_r_2g6_ .cluster rect{fill:rgb(243, 243, 243);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_2g6_ .cluster text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2g6_ .cluster span{color:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2g6_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(243, 243, 243);border:1px solid rgba(0, 0, 0, 0.1);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_2g6_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(13, 13, 13);}#chatgpt-mermaid-_r_2g6_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_2g6_ .icon-shape,#chatgpt-mermaid-_r_2g6_ .image-shape{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-_r_2g6_ .icon-shape p,#chatgpt-mermaid-_r_2g6_ .image-shape p{background-color:rgb(252, 252, 252);padding:2px;}#chatgpt-mermaid-_r_2g6_ .icon-shape .label rect,#chatgpt-mermaid-_r_2g6_ .image-shape .label rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-_r_2g6_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_2g6_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_2g6_ .node .neo-node{stroke:rgb(83, 154, 248);}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_2g6_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_2g6_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_2g6_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_2g6_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].node .neo-line path{stroke:rgb(83, 154, 248);filter:none;}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_2g6_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_2g6_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2g6_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_2g6_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_2g6_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(0, 79, 153);}#chatgpt-mermaid-_r_2g6_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(0, 79, 153);}#chatgpt-mermaid-_r_2g6_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_2g6_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_2g6_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-width:1px;}#chatgpt-mermaid-_r_2g6_ .node rect,#chatgpt-mermaid-_r_2g6_ .node circle,#chatgpt-mermaid-_r_2g6_ .node ellipse,#chatgpt-mermaid-_r_2g6_ .node polygon,#chatgpt-mermaid-_r_2g6_ .node path{fill:rgb(229, 243, 255);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_2g6_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_2g6_ .mermaid-decision .label-container{fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_2g6_ .edgePaths .flowchart-link{stroke:rgb(143, 143, 143);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_2g6_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-_r_2g6_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Support agent opens ticketRequest tenant accessProvide reason and scopeAuthorize accessCreate time-limited sessionInspect permitted tenant dataRecord all actionsAccess expires or is revoked





29. Recommended Super Admin database modules
Your FastAPI backend should keep Super Admin functionality separated into its own modules, while reusing the existing tenant, user and subscription domain services.

Suggested structure:
backend/app/
├── modules/
│   ├── platform_admin/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── repository.py
│   │
│   ├── tenants/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── repository.py
│   │
│   ├── subscriptions/
│   ├── plans/
│   ├── billing/
│   ├── payments/
│   ├── invoices/
│   ├── platform_users/
│   ├── support/
│   ├── notifications/
│   ├── feature_flags/
│   ├── integrations/
│   ├── analytics/
│   ├── audit_logs/
│   ├── monitoring/
│   ├── onboarding/
│   └── platform_settings/
│
└── api/
    └── v1/
        └── routes/
            └── admin.py


Recommended core database tables:
Table	Purpose
tenants	Restaurant businesses
branches	Restaurant locations
users	Global user accounts
tenant_memberships	User-to-tenant relationships
platform_admin_roles	Platform administrator roles
platform_admin_permissions	Fine-grained permissions
subscription_plans	Available plans
plan_features	Plan feature definitions
subscriptions	Restaurant subscriptions
subscription_events	Subscription history
payments	SaaS payment transactions
invoices	Billing documents
coupons	Promotional codes
support_tickets	Customer support
notifications	Platform communications
feature_flags	Controlled feature releases
audit_logs	Administrative activity
integration_configs	Integration settings
webhook_events	Integration event history
data_export_jobs	Tenant data exports
platform_incidents	Service incidents

You will need additional tables for invoice items, payment refunds, support messages, notification deliveries, feature targeting and other details as these modules are implemented.
30. Critical security rules for Super Admin
This is where I would be strict during implementation.
1. Separate authentication and authorization: Super Admin access must require an explicit platform role, not merely a restaurant owner account.
2. MFA: Require multi-factor authentication for platform administrators.
3. Least privilege: Finance administrators should not automatically have access to security settings.
4. Tenant isolation: Every tenant-specific operation must validate the target tenant and prevent cross-tenant access.
5. Audit everything: Record sensitive administrative actions, including actor, target, reason and timestamp.
6. No silent impersonation: Support access must be scoped, time-limited and audited.
7. Secure payments: Only verified backend payment events can activate or renew subscriptions.
8. Protect secrets: Never expose provider API keys or credentials in API responses.
9. Protect data deletion: Require authorization, confirmation, retention checks and an auditable deletion workflow.
10. Background jobs: Every tenant-specific job must carry and validate tenant context.
A further architectural recommendation: use a separate platform-admin authorization dependency in FastAPI. Do not simply reuse a restaurant-manager dependency and give it extra permissions.
31. What should you build first?
I would not build all these modules simultaneously. Some are essential for launching your SaaS; others are operational improvements that can come later.
Priority 1 — Required for commercial launch
MVP
- Super Admin authentication and MFA
- Dashboard
- Restaurant/tenant management
- Subscription plan management
- Subscription lifecycle management
- Payment and invoice management
- Platform user and role management
- Audit logs
- Platform settings
- Tenant diagnostics
  
  Priority 2 — Operational maturity
  Next release
- Support ticket management
- Notifications and announcements
- Onboarding monitoring
- Branch overview
- Business analytics
- Integration management
- Feature flags
- Incident management
- Backup monitoring
  
  Priority 3 — Advanced SaaS platform
  Later release
- Promotions and referral system
- Website CMS
- API and developer portal
- Advanced data governance
- Automated reconciliation
- Advanced usage analytics
- Customer success automation

32. My recommendation for the final Super Admin product
Your Super Admin should have three levels of responsibility:
Level	Responsibility
Business control	Restaurants, subscriptions, billing and revenue
Operational control	Support, onboarding, integrations and tenant diagnostics
Technical control	Security, audit logs, monitoring, backups and incidents

One important design decision: Super Admin should be able to oversee every restaurant, but should not routinely operate restaurants on their behalf. Restaurant owners remain responsible for their own daily operations.

This separation makes the system easier to secure, scale and sell to more restaurant businesses.
