# Phase 15 — Reviews & Reputation Management Plan

## Objective
Enable collection and display of customer ratings and feedback, integration with external review platforms (Google Business Profile), and review analytics to help restaurants manage their online reputation and improve service quality.

## Scope
### Implemented (Foundation)
- `OrderRating` model — rating (1-5 integer) and `comment` text per order
- Public order status API — customers can view order status via status token
- Basic order-level rating collection triggered at order completion

### New / Planned

1. **Customer Ratings & Reviews**
   - Post-order rating: 1-5 stars with optional written feedback
   - Ratings linked to order via `order_id`; customer identified by `customer_status_token_hash` or registered `customer` profile
   - Rating submission window: within 24-48 hours after order COMPLETED
   - Edit/cancel rating window: 15-30 minutes after submission (prevents rage editing)
   - Average rating display: per restaurant, per branch, per dish/category (if linked)
   - Star distribution chart: percentage of 1-star, 2-star, ..., 5-star ratings

2. **Review Themes & Tags**
   - Predefined themes: food quality, service, ambiance/atmosphere, value/wait time, parking, delivery speed
   - Customer can select multiple themes + write open text
   - Employee linkage: if feedback references service, link to employee shift for coaching
   - Heatmap of common praise/complaints per restaurant

3. **External Review Platform Integration**
   - "Submit to Google" button: generates Google review link (with pre-filled text, restaurant name, visit date)
   - Cannot publish own website reviews as Google reviews (policy constraint noted in feature list)
   - Track Google review URL per restaurant
   - Import existing Google reviews (if connected via Google Business Profile API)
   - Display review count and average rating from Google alongside own ratings

4. **Review Moderation**
   - Flag reviews for moderation: spam, offensive content, unrelated to this restaurant
   - Manager can hide/flag reviews
   - Report review to platform (Google, if integrated)
   - Response from restaurant: managers can reply to visible reviews (public response)
   - Review guidelines/terms displayed at submission

5. **Review Analytics & Reports**
   - Average rating trend over time (daily/weekly/monthly)
   - Theme distribution: which aspects get highest/lowest scores
   - Review volume per period
   - Employee-level ratings: if service feedback linked to employee
   - Comparison vs competitors (if using third-party review aggregation service)
   - Export reviews for external analysis (CSV)

6. **Response Management**
   - Manager can reply to visible reviews (public response visible to all)
   - Response text stored and displayed with review
   - Notification to manager when new review received
   - Escalation: negative ratings < 3 stars notify manager immediately
   - Template responses for common scenarios (apology, thanks, resolution offer)

7. **Customer Review History**
   - Customer can view their own submission history (if registered account)
   - Customer can edit/cancel within window
   - Customer can see average rating they've given across all restaurants (if across-chain)
   - GDPR: customer can request deletion of their review history

## Technical Design

### New Models (to be created)
- `Review` — order_id (FK, nullable; link to order if identified), customer_identifier (hashed token or customer_id), rating (1-5), theme(s): set of enum, open_text, created_at, updated_at, is_visible, status (PENDING, VISIBLE, HIDDEN, FLAGGED), manager_response_text, manager_response_at
- `ReviewTheme` — name (unique), category (FOOD, SERVICE, AMBIANCE, VALUE, DELIVERY, PARKING), description
- `ReviewResponse` — review_id, manager_id, response_text, responded_at, is_public
- `ReviewFlag` — review_id, flagged_by_manager_id, reason (SPAM, OFFENSIVE, OFF_TOPIC, DUPLICATE), created_at, resolved_at, resolution_notes
- `GoogleBusinessLink` — restaurant_id, business_id (Google's ID), review_url, last_sync_at, sync_status (SYNCING, SYNCED, ERROR)

### Existing Models to Extend
- `OrderRating` — extend with: `theme(s)` (set of ReviewTheme), `would_recommend` (boolean, optional), `helpful_votes` (integer, default 0, for future community voting), `is_visible` (boolean, default True; toggle for moderation), `linked_employee_id` (FK, optional)
- `RestaurantSettings` — add: `reviews_enabled`, `allow_google_integration`, `review_response_enabled`, `review_moderation_enabled`, `review_response_template_apology`, `review_response_template_thanks`, `review_minimum_stars_for_notification`

### API Endpoints (planned)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/ratings` | List ratings for restaurant/branch (filtered by visible, theme, date range) |
| `POST /api/v1/ratings` | Submit rating for order |
| `GET /api/v1/ratings/{id}` | Get rating detail |
| `PATCH /api/v1/ratings/{id}` | Edit rating (within window), update theme/text |
| `POST /api/v1/ratings/{id}/flag` | Flag review for moderation |
| `PATCH /api/v1/ratings/{id}/response` | Add manager response |
| `GET /api/v1/ratings/stats` | Rating statistics: average, distribution, volume, trends |
| `GET /api/v1/ratings/themes` | List available review themes |
| `GET /api/v1/google-business` | Get Google Business link and sync status |
| `POST /api/v1/google-business/sync` | Trigger Google review sync |

### Schemas (new or extended)
- `RatingOut` — id, order, rating, theme(s), open_text, customer_identifier, created_at, is_visible, linked_employee
- `RatingIn` — order_id, customer_identifier, rating, theme_ids, open_text
- `ReviewThemeOut` — id, name, category
- `RatingStatsOut` — average_rating, distribution_{1-5}, total_count, period_start, period_end, trend (improving/declining/stable)
- `GoogleBusinessLinkOut` — business_id, review_url, last_sync_at, sync_status

### Integration Points
- **Orders**: Rating submitted after order COMPLETED; linked to order; optionally linked to customer
- **Payments**: No direct impact; rating is feedback separate from payment
- **Dashboard**: Rating widgets: average rating, distribution, trend, theme heatmap, review volume, employee performance (if service-linked)
- **Email**: Notification to manager when new review received (especially < 3 stars); weekly summary report
- **Google Business**: Sync bidirectional: pull reviews in, push rating average out
- **Audit**: All rating actions (submit, edit, flag, response, hide) audited
- **Outbox**: Review events (new rating, response posted) for external system sync

### Configuration
- Rating window: hours after order completion (default 24)
- Edit window: minutes after submission (default 15)
- Minimum stars for manager notification (default: < 3)
- Themes mandatory vs optional (configurable)
- Google Business sync: hourly/daily/manual
- Review response: enabled/disabled per restaurant
- Minimum review count before displaying average publicly (e.g., need 5 ratings before showing 4.2 stars)

## Migration / Rollout Plan
- **Phase 1**: Extend `OrderRating` with themes, visibility, would_recommend; add `Review` model for longer-term storage; add themes enum
- **Phase 2**: Review moderation (flag/hide), manager responses, Google Business link
- **Phase 3**: Rating statistics API, theme heatmap, review themes configurability
- **Phase 4**: Customer review history, response management, export/csv

Rollback at any phase: revert `OrderRating` extensions, remove new models (`Review`, `ReviewTheme`, etc.), revert API routes, keep existing rating data visible.

## Acceptance Criteria
- [ ] Customer can submit 1-5 star rating with optional text after order completion
- [ ] Rating themes selectable; open text optional
- [ ] Rating editable/cancellable within configured window
- [ ] Average rating displayed on restaurant page/dashboard
- [ ] Theme distribution shown in dashboard
- [ ] Manager notified when rating < 3 stars
- [ ] Manager can add public response to rating
- [ ] Google Business link configured; sync pulls/reviews
- [ ] Review flagging and hiding works
- [ ] All rating actions appear in audit trail
- [ ] Existing 73 isolation tests continue to pass
- [ ] 100% of new unit tests pass

## Open Questions / Dependent Work
- Should reviews be linked to customer accounts or anonymous tokens primarily? (anonymous preferred for frictionless submission, accounts for history)
- How to handle fake/Spam reviews at scale? (rate limiting, IP tracking, moderation queue)
- Response templates: configurable per restaurant or global defaults?
- Integration with which Google Business API scope? (read-only vs write)
- Review response visibility: always public, or owner-choice per review?
- Minimum review count before showing average publicly (SEO vs new restaurant boost)?
- Integration with Facebook/TripAdvisor reviews (future, after Google)?

## Phase Order Relative to Other Work
- **Before**: SaaS subscriptions (reviews as feature; could be tier-gated), Employee (employee linking of service feedback), Multi-branch (per-branch ratings vs consolidated)
- **After**: Reports (reviews analytics dashboard is a major component), Customer loyalty (ratings feed into loyalty program: review = points), SaaS management (feature toggle for reviews on/off per tenant)
- **Parallel potential**: Employee + Reviews (link service feedback to specific employee for coaching), Dashboard + Loyalty (review-based tier bonuses)