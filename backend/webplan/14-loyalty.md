# Phase 14 — Customer Loyalty & Rewards Plan

## Objective
Enable customer profiles, order history, loyalty points, reward programs, discount coupons, and promotional offers to increase customer retention and lifetime value. This is a key differentiator for competing as a complete restaurant SaaS.

## Scope
### Implemented (Foundation)
- `Order` model with `customer_status_token_hash` and `customer_note` — captures anonymous QR customer identity
- `OrderRating` model — rating (1-5) and comment per order
- Public order status API — customers can track their order status via token
- Basic feedback collection through ratings

### New / Planned

1. **Customer Profiles**
   - Customer sign-up: name, email, phone (with consent), preferred dining times, dietary restrictions
   - Anonymous QR customer: token-based profile linked to orders via `customer_status_token_hash`
   - Customer preferences: favorite dishes, spice level, seating preference, notification preferences
   - Birthday info: stored with consent, used for birthday rewards
   - Account deletion/GDPR right to be forgotten

2. **Loyalty Points Program**
   - Points earned per order: 1 point per $1 spent (configurable rate)
   - Points per visit: bonus for repeat visits within N days
   - Points per review: +50 points for submitted rating
   - Points expiration: after 12 months of inactivity
   - Point balance display: customer dashboard, server-facing view
   - Points redemption: redeem points for discounts (e.g., 100 points = $1 off)

3. **Reward Programs**
   - Tiered loyalty: Bronze (0-999 pts), Silver (1000-4999 pts), Gold (5000+ pts)
   - Tier benefits: free drink on birthday, priority seating, exclusive discounts, double points month
   - Program configuration per restaurant: earn rate, redeem rate, tier thresholds, expiration
   - Multiple loyalty programs per restaurant (e.g., "Lunch Club" vs "Dinner Elite")

4. **Discount Coupons & Promotional Offers**
   - Create coupons: percentage off, fixed amount off, free item, free delivery
   - Coupon validity: start/end date, usage limits per customer, usage limits total, minimum order value
   - Promotional offers: "Buy 1 Get 1 Free", "Happy Hour 20% off", "First order 25% off"
   - Coupon code generation and display for marketing
   - Redeem at POS/bill payment time
   - Track coupon ROI (how many redeemed, total discount given, incremental revenue)

5. **Referral Program**
   - Existing customer refers new customer via unique referral link/code
   - Both get rewarded: referrer gets points/fixed amount, referee gets signup bonus
   - Referral tracking: new customer attribution, first order linkage
   - Referral program configuration per restaurant

6. **Customer Feedback & Surveys**
   - Post-order survey: 1-5 rating, multiple choice (food quality, service, ambiance, value), open text
   - Survey triggered after order COMPLETED (within 24h)
   - Feedback summary per restaurant: average scores, common themes
   - Link feedback to employee if service-related
   - Export feedback for external review platforms

7. **Customer Segmentation & Reports**
   - New vs returning customer rate
   - Frequency: orders per 30/60/90 days
   - Monetary: average spend per order, per customer, per period
   - Recency: days since last order
   - Top customers: highest lifetime value, most frequent
   - Segment by: branch, time period, loyalty tier, order type (dine-in vs takeout vs delivery)

8. **Integrated Marketing**
   - Email/SMS notification preferences per customer
   - Birthday email with coupon (automated via outbox)
   - Anniversary of first order celebration
   - Re-engagement campaign for dormant customers (no orders in N days)
   - Preference center: unsubscribe, modify communication preferences

## Technical Design

### New Models (to be created)
- `Customer` — user_id (FK, nullable; anonymous QR customer has NULL user_id), restaurant_id, branch_id (nullable), name, email (hashed, with consent), phone (hashed, with consent), birthday, preferences_json, status (ACTIVE, INACTIVE, DELETED), created_at, updated_at, last_order_at
- `LoyaltyProgram` — restaurant_id, name, earn_rate (points_per_dollar), redeem_rate (dollars_per_point), tier_thresholds (JSON: {bronze: 0, silver: 1000, gold: 5000}), expiration_days, is_active
- `LoyaltyAccount` — customer_id, program_id, current_balance, total_earned, total_redeemed, tier, last_earned_at, last_redeemed_at, points_expiration_date
- `PointTransaction` — loyalty_account_id, order_id (nullable), type (EARN/REDEEM/EXPIRE/BONUS), amount, balance_after, created_at, reference_id (order_id or coupon_id or manual)
- `Coupon` — restaurant_id, code, type (percentage, fixed, free_item, buy_one_get_one), amount_or_percentage, min_order_value, max_uses, uses_count, start_date, end_date, is_active, created_by (manager_id)
- `CouponRedemption` — coupon_id, customer_id (or anonymous_token), order_id, redeemed_at, discount_amount, status (USED, VOIDED)
- `Referral` — referrer_customer_id (or anonymous_token), referee_customer_id (or email), referee_signup_date, referee_first_order_id, referrer_reward_status (PENDING, AWARDED), referee_reward_status (PENDING, AWARDED), created_at
- `Survey` — restaurant_id, question_text, question_type (rating, multiple_choice, open_text), options (for multiple_choice), is_active, created_at
- `SurveyResponse` — survey_id, customer_id (or anonymous_token), responses_json (structured), completed_at, employee_id (if linked to service)

### Existing Models to Extend
- `Order` — extend with: `loyalty_account_id` (FK, nullable; links to customer loyalty if identified), `referral_code` (generated or provided), `coupon_code` (applied at submission)
- `OrderRating` — extend with: `feedback_theme` (food/service/ambiance/value), `would_ recommend` (boolean), `follow_up_required` (boolean)
- `RestaurantSettings` — add: `loyalty_enabled`, `default_earn_rate`, `default_redeem_rate`, `birthday_coupon_enabled`, `referral_program_enabled`

### API Endpoints (planned)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/customers` | List customers (filtered by branch/restaurant, search by name/email) |
| `POST /api/v1/customers` | Create customer profile |
| `GET /api/v1/customers/{id}` | Get customer detail with loyalty balance |
| `PATCH /api/v1/customers/{id}` | Update preferences, birthday, consent |
| `GET /api/v1/loyalty-programs` | List active loyalty programs |
| `GET /api/v1/loyalty-accounts/{id}` | Get customer loyalty balance and history |
| `POST /api/v1/point-transactions` | Manual point award/deduction (manager) |
| `GET /api/v1/coupons` | List active coupons |
| `POST /api/v1/coupons` | Create coupon (manager) |
| `POST /api/v1/coupons/{id}/redeem` | Redeem coupon on order |
| `GET /api/v1/referrals` | List referrals for restaurant |
| `POST /api/v1/surveys` | Create survey |
| `POST /api/v1/survey-responses` | Submit survey response |
| `GET /api/v1/customers/{id}/reports` | Customer segmentation report |

### Schemas (new or extended)
- `CustomerOut` — id, name, email (hashed prefix), phone (hashed prefix), birthday, preferences, loyalty_tier, balance, status
- `CustomerIn` — name, email (hashed), phone (hashed), birthday, preferences, consent_marketing, consent_data
- `LoyaltyProgramOut` — id, name, earn_rate, redeem_rate, tiers, is_active
- `LoyaltyAccountOut` — current_balance, total_earned, total_redeemed, tier, points_expiring_soon, earning_rate
- `PointTransactionOut` — type, amount, balance_after, created_at, reference (order/coupon)
- `CouponOut` — id, code, type, amount, min_order_value, uses_count/max_uses, start/end, is_active
- `ReferralOut` — referrer, referee, both_rewards_status, referral_link
- `SurveyOut` — id, question, type, is_active
- `SurveyResponseOut` — id, customer, completed_at, responses

### Integration Points
- **Orders**: Loyalty points earned on order completion; coupon codes applied; referral tracking
- **Payments**: Discount from coupon reduces total; points redemption reduces amount
- **Dashboard**: Loyalty analytics: balance distribution, tier breakdown, top customers, redemption rate
- **Email/SMS**: Automated campaigns (birthday, re-engagement) via outbox service
- **Survey**: Trigger after order COMPLETED; link response to order
- **Audit**: All loyalty transactions audited (points earned/redeemed, coupon usage, referrals)
- **Outbox**: Loyalty event emissions (points earned, tier upgraded, birthday coupon generated)

### Configuration
- Earn rate: points per dollar (or per order, or per item — configurable per restaurant)
- Redeem rate: dollar value of point (e.g., 100 points = $1)
- Tier thresholds: customizable per restaurant
- Points expiration: configurable (30/60/90/365 days inactivity)
- Coupon stacking: allow/disallow multiple coupons per order
- Referral rewards: fixed points or fixed dollar amount for both parties
- Survey timing: hours after order completion

## Migration / Rollout Plan
- **Phase 1**: Customer model, loyalty program model, basic earn on order completion
- **Phase 2**: Loyalty accounts, point transactions, tier system
- **Phase 3**: Coupons, referrals, surveys
- **Phase 4**: Customer reports, segmentation, marketing integrations (email/SMS outbox)
- **Phase 5**: GDPR/privacy controls, data retention, account deletion

Rollback at any phase: remove new tables/columns, revert API routes, disable loyalty features via `RestaurantSettings.loyalty_enabled`, keep existing order/rating data.

## Acceptance Criteria
- [ ] Customer can be created (anonymous QR or registered)
- [ ] Loyalty points earned automatically on order completion (configurable rate)
- [ ] Points balance visible in customer detail and dashboard
- [ ] Tier thresholds applied correctly; tier changes as balance crosses boundary
- [ ] Coupons created, displayed with code, redeemable at bill payment
- [ ] Referral program: both parties receive rewards on referee's first order
- [ ] Post-order survey triggered and responses stored
- [ ] Customer segmentation reports: returning/ new, frequency, monetary, recency
- [ ] All loyalty actions audited
- [ ] Existing 73 isolation tests continue to pass
- [ ] 100% of new unit tests pass

## Open Questions / Dependent Work
- Integration with email marketing service (Mailchimp, SendGrid) or internal outbox only?
- Should customer profiles merge when same email used at different branches?
- Points expiration: sliding window vs fixed anniversary date?
- Coupon stacking: allow percentage + fixed together? or one per order?
- Integration with review platforms (Google, TripAdvisor) — push satisfied customers?
- GDPR data retention period for inactive customers (1yr/3yr/7yr)?
- SMS integration cost vs benefit for birthday/anniversary messages?

## Phase Order Relative to Other Work
- **Before**: Multi-branch (loyalty per-branch or consolidated?), Employee (staff can note repeat customers), Inventory (not directly related but affects "favorite dishes" tracking)
- **After**: SaaS subscriptions (loyalty as feature access tier), Reports (loyalty analytics dashboard), SaaS management (feature flags for loyalty on/off per tenant)
- **Parallel potential**: Billing + Loyalty (points earning on payments, coupon redemption), Dashboard (loyalty widgets alongside revenue)