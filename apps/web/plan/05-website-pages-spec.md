# Website Plan — Pages Specifications

## Overview
Detailed specifications for all website pages in the multi-tenant restaurant SAAS platform. Each page includes wireframe description, API calls, component usage, and responsive behavior.

## Page Navigation Flow

```
Landing
  ↓ (Sign Up/Login)
Auth Pages
  ↓
Dashboard (tier-dependent)
  ↓
Branch Management (Professional+)
  ↓
Table Management (All tiers)
  ↓
QR Ordering (All tiers)
  ↓
Audit Viewer (Enterprise+)
  ↓
Admin Portal (Enterprise+)
```

## Page 1: Landing Page

### URL
`/`

### Tier
All (public)

### Wireframe Description
- **Hero Section**: Large headline, subheadline, CTA button ("Get Started")
- **Features Section**: 3-column grid with icons and descriptions
- **Pricing Section**: Tier cards (Basic, Professional, Enterprise) with feature comparison
- **Testimonials**: Customer quotes with ratings
- **Footer**: Links, contact info, social media

### Components Used
- Hero banner with gradient background
- Feature cards with icons
- Pricing cards with tier highlighting
- Testimonial carousel
- Footer with newsletter signup

### API Calls
- None (public page)

### Responsive Behavior
- **Mobile**: Single column, stacked sections
- **Tablet**: 2-column features, single pricing column
- **Desktop**: 3-column features, 3-column pricing

### Accessibility
- Skip navigation link
- Alt text for all images
- Keyboard navigable CTAs
- Color contrast: 4.5:1 minimum

## Page 2: Authentication Pages

### URL
`/login`, `/register`, `/reset-password`

### Tier
All

### Wireframe Description
- **Login Form**: Email, password, remember me, forgot password link
- **Register Form**: Name, email, password, confirm password, restaurant name
- **Reset Password**: Email input, send reset link, new password form
- **Social Login**: Google, Apple, Microsoft (future)

### Components Used
- Form inputs with validation
- Password strength meter
- Social login buttons
- Loading spinner for submission
- Error/success toast notifications

### API Calls
- `POST /api/auth/login` — Login with email/password
- `POST /api/auth/register` — Create account + restaurant
- `POST /api/auth/reset-password` — Request reset link
- `POST /api/auth/confirm-reset` — Confirm new password

### Responsive Behavior
- **Mobile**: Full-width form, stacked layout
- **Tablet**: Centered card layout
- **Desktop**: Centered card layout with side illustration

### Accessibility
- Form labels with `for` attributes
- Error messages with `aria-live`
- Password visibility toggle with `aria-label`
- Keyboard navigation for all fields

## Page 3: Dashboard

### URL
`/dashboard`

### Tier
Basic+, Professional+, Enterprise+

### Wireframe Description
- **Header**: Welcome message, tenant selector, notifications
- **Quick Stats**: Orders today, revenue, occupancy, QR scans
- **Quick Actions**: Add table, create QR, view orders
- **Recent Activity**: Latest orders, table changes
- **Branch Selector**: Switch between branches (Professional+)

### Components Used
- Stat cards with icons and trends
- Quick action buttons
- Activity feed with timestamps
- Branch selector dropdown
- Loading skeletons

### API Calls
- `GET /api/dashboard/stats` — Quick stats
- `GET /api/dashboard/branches` — Branch list (Professional+)
- `GET /api/dashboard/activity` — Recent activity

### Responsive Behavior
- **Mobile**: Single column, stacked cards
- **Tablet**: 2-column layout
- **Desktop**: 3-4 column layout with sidebar

### Accessibility
- ARIA labels for stat cards
- Live regions for real-time updates
- Keyboard navigation for quick actions

## Page 4: Branch Management

### URL
`/branches`

### Tier
Professional+, Enterprise+

### Wireframe Description
- **Header**: "Branches" title, "Add Branch" button
- **Branch List**: Table with name, location, hours, status, actions
- **Branch Card**: Visual representation with stats
- **Add Branch Modal**: Form for new branch details
- **Edit Branch Modal**: Update branch info
- **Suspend/Reactivate**: Status toggle with confirmation

### Components Used
- Data table with sorting/filtering
- Branch cards with stats
- Modal dialogs for add/edit
- Status badges (active, suspended)
- Confirmation dialogs

### API Calls
- `GET /api/branches` — List branches
- `POST /api/branches` — Create branch
- `GET /api/branches/:id` — Get branch details
- `PUT /api/branches/:id` — Update branch
- `DELETE /api/branches/:id` — Suspend branch
- `POST /api/branches/:id/reactivate` — Reactivate branch

### Responsive Behavior
- **Mobile**: Card view, single column
- **Tablet**: 2-column card grid
- **Desktop**: Table view with all columns

### Accessibility
- Table headers with `scope`
- Action buttons with `aria-label`
- Modal focus management
- Status announcements

## Page 5: Table Management

### URL
`/tables`

### Tier
All tiers

### Wireframe Description
- **Header**: "Tables" title, "Add Table" button, branch selector
- **Table Grid**: Visual grid of tables with status
- **Table Card**: Table name, capacity, status, QR code
- **Add Table Modal**: Table code, name, capacity, branch
- **Edit Table Modal**: Update table details
- **QR Code Modal**: Generate/rotate QR code

### Components Used
- Grid layout with draggable cards
- Table status indicators
- Modal dialogs for CRUD operations
- QR code display with download
- Capacity selector

### API Calls
- `GET /api/tables` — List tables
- `POST /api/tables` — Create table
- `GET /api/tables/:id` — Get table details
- `PUT /api/tables/:id` — Update table
- `DELETE /api/tables/:id` — Archive table
- `POST /api/tables/:id/qr/rotate` — Rotate QR code

### Responsive Behavior
- **Mobile**: 2-column grid
- **Tablet**: 3-column grid
- **Desktop**: 4-column grid with sidebar

### Accessibility
- Drag-and-drop with keyboard alternatives
- Status announcements
- QR code alt text
- Table selection with `aria-selected`

## Page 6: QR Ordering (Customer-Facing)

### URL
`/qr/:token`

### Tier
All tiers

### Wireframe Description
- **Header**: Restaurant name, logo, table number
- **Menu Section**: Categories, items with images/prices
- **Cart**: Slide-out cart with quantity, subtotal
- **Order Status**: Real-time order status updates
- **Bill Section**: View bill, payment options

### Components Used
- Menu categories with accordion
- Item cards with add-to-cart
- Cart drawer with quantity controls
- Order status tracker
- Bill summary with payment buttons

### API Calls
- `GET /api/qr/:token` — Get restaurant/table info
- `GET /api/qr/:token/menu` — Get menu
- `POST /api/qr/:token/orders` — Place order
- `GET /api/orders/:status_token` — Order status
- `GET /api/orders/:status_token/bill` — Bill details

### Responsive Behavior
- **Mobile**: Full-screen cart, single column menu
- **Tablet**: 2-column menu, slide-out cart
- **Desktop**: 3-column menu, persistent cart sidebar

### Accessibility
- Touch-friendly buttons (44px minimum)
- Screen reader announcements for cart updates
- Focus management for modal dialogs
- High contrast mode support

## Page 7: Audit Viewer

### URL
`/audit`

### Tier
Enterprise+ only

### Wireframe Description
- **Header**: "Audit Logs" title, filters (date, user, action)
- **Log Table**: Timestamp, user, action, details, outcome
- **Filters**: Date range, user selector, action type, status
- **Export Button**: Export to CSV/JSON
- **Pagination**: Page navigation

### Components Used
- Data table with sorting/filtering
- Date range picker
- Multi-select filters
- Export button with format options
- Pagination controls

### API Calls
- `GET /api/audit/logs` — List audit logs
- `GET /api/audit/export` — Export audit logs
- `GET /api/audit/filters` — Available filter options

### Responsive Behavior
- **Mobile**: Card view, stacked filters
- **Tablet**: Table view with horizontal scroll
- **Desktop**: Full table view with all columns

### Accessibility
- Table headers with `scope`
- Filter labels with `aria-label`
- Export button with `aria-describedby`
- Pagination with `aria-current`

## Page 8: Admin Portal

### URL
`/admin`

### Tier
Enterprise+ only

### Wireframe Description
- **Sidebar**: Navigation (users, plans, settings, analytics)
- **User Management**: List users, roles, permissions
- **Plan Management**: View/edit subscription plans
- **Settings**: System settings, integrations
- **Analytics**: Usage metrics, revenue reports
- **Billing**: Invoices, payment history

### Components Used
- Admin sidebar navigation
- User management table
- Plan configuration forms
- Settings panels
- Analytics charts
- Billing tables

### API Calls
- `GET /api/admin/users` — List users
- `POST /api/admin/users` — Create user
- `GET /api/admin/plans` — List plans
- `PUT /api/admin/plans/:id` — Update plan
- `GET /api/admin/settings` — System settings
- `PUT /api/admin/settings` — Update settings
- `GET /api/admin/analytics` — Usage metrics
- `GET /api/admin/billing` — Billing history

### Responsive Behavior
- **Mobile**: Simplified view, limited features
- **Tablet**: Collapsed sidebar, main content
- **Desktop**: Full sidebar + content layout

### Accessibility
- Admin-specific ARIA labels
- Keyboard shortcuts for power users
- Screen reader announcements for admin actions
- Focus management for modal dialogs

## Data Flow Summary

### Authentication Flow
1. User visits `/login`
2. Enter credentials → `POST /api/auth/login`
3. Backend verifies → returns JWT with `tenant_id`, `mid`, `rid`
4. Store JWT in localStorage/HttpOnly cookie
5. Set `x-tenant-id` header on subsequent requests
6. Backend `get_actor()` validates tenant + membership
7. User redirected to `/dashboard`

### Branch Management Flow
1. User visits `/branches`
2. `get_actor()` retrieves tenant from `tenant_context`
3. API call `/api/branches` with tenant context
4. Backend returns branches for that tenant only (RLS)
5. Display branch list with management actions
6. Actions trigger `/api/branches` POST/PUT/DELETE
7. RLS ensures data isolation

### QR Ordering Flow
1. User visits `/qr/:token`
2. Backend validates token + tenant from QR
3. Display menu for that tenant's restaurant
4. User adds items to cart
5. Submit order → `/api/orders`
6. Order associated with tenant's branch
7. Kitchen receives order via kitchen display system

## Navigation Flow

### Basic Tier
```
Landing → Auth → Dashboard → Table Management → QR Ordering
```

### Professional Tier
```
Landing → Auth → Dashboard → Branch Management → Table Management → QR Ordering → Audit Viewer
```

### Enterprise Tier
```
Landing → Auth → Dashboard → Branch Management → Table Management → QR Ordering → Audit Viewer → Admin Portal
```

---
*Page specifications aligned with 26-phase backend implementation. All pages designed for production-grade SAAS with multi-tenant isolation and responsive design.*