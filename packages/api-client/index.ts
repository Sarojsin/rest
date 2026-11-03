/**
 * Platform-neutral API client and response types shared by the React website
 * and the React Native staff app.
 *
 * Nothing in here may import a DOM API, a React Native module, or a storage
 * backend: callers inject `baseUrl` and `getToken`. Money is always integer
 * minor units, straight from the server.
 */

/* -------------------------------------------------------------------------
   Errors
   ------------------------------------------------------------------------- */

export type Problem = {
  type?: string;
  title?: string;
  status?: number;
  code?: string;
  detail?: string;
  request_id?: string;
};

export class ApiError extends Error {
  status: number;
  code: string;
  detail: string;

  constructor(status: number, code: string, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

/** Network/timeout failure — the request outcome is unknown to the client. */
export class ApiTransportError extends Error {
  kind: "timeout" | "offline" | "aborted";

  constructor(kind: "timeout" | "offline" | "aborted", message: string) {
    super(message);
    this.name = "ApiTransportError";
    this.kind = kind;
  }
}

/* -------------------------------------------------------------------------
   Client
   ------------------------------------------------------------------------- */

export type ApiRequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  /** JSON string or multipart body (file uploads). */
  body?: string | FormData;
  /** Caller-owned cancellation. */
  signal?: AbortSignal;
  /** Sent as `Idempotency-Key`; required by order/payment mutations. */
  idempotencyKey?: string;
  /** Overrides the client default for this request. */
  timeoutMs?: number;
};

export type ApiClientConfig = {
  /** Empty string for same-origin (website behind a proxy). */
  baseUrl: string;
  /** Sync or async token lookup; the client never caches the token itself. */
  getToken: () => string | null | Promise<string | null>;
  /**
   * Called when an authenticated request is rejected with 401 so the app can
   * drop the session. Never fired for unauthenticated requests (e.g. login).
   */
  onUnauthorized?: () => void;
  /** Default request timeout. */
  timeoutMs?: number;
};

export type ApiClient = {
  request: <T>(path: string, options?: ApiRequestOptions) => Promise<T>;
  /** Bearer header for endpoints that return bytes (payment QR images). */
  authHeaders: () => Promise<Record<string, string>>;
  /** Absolute URL for a path, for image sources that bypass the client. */
  url: (path: string) => string;
}

/* -------------------------------------------------------------------------
   Tenancy / Restaurant
   ------------------------------------------------------------------------- */

export type RestaurantOut = {
  id: string;
  name: string;
  slug: string;
  timezone: string;
  currency_code: string;
  tax_rate_bps: number;
  qr_ordering_enabled: boolean;
  customer_hostname: string;
};

export type CustomerHostOut = {
  customer_subdomain: string;
  custom_domain: string | null;
  customer_hostname: string;
  brand_logo_url: string;
  brand_accent_hex: string | null;
};

/* -------------------------------------------------------------------------
   Identity / Auth
   ------------------------------------------------------------------------- */

export type Membership = {
  id: string;
  restaurant_id: string;
  restaurant_name: string;
  role: string;
  permissions: string[];
};

export type Me = {
  id: string;
  email: string;
  display_name: string;
  membership: Membership;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: Me;
};

/* -------------------------------------------------------------------------
   Catalog / Menu
   ------------------------------------------------------------------------- */

export type MenuItem = {
  id: string;
  name: string;
  description: string;
  current_price_minor: number;
  currency_code: string;
  status: string;
  display_order: number;
  image_emoji: string;
  image_path?: string;
  model_path?: string;
  ingredients_text?: string;
  category_id?: string;
};

export type MenuCategory = {
  id: string;
  name: string;
  description: string;
  display_order: number;
  status?: string;
  items: MenuItem[];
};

export type PublicMenu = {
  restaurant_name: string;
  currency_code: string;
  table_id: string;
  table_display_name: string;
  qr_ordering_enabled: boolean;
  categories: MenuCategory[];
};

/* -------------------------------------------------------------------------
   Operations / Tables & Orders
   ------------------------------------------------------------------------- */

export type Table = {
  id: string;
  table_code: string;
  display_name: string;
  seating_capacity: number | null;
  status: string;
  sort_order: number;
  occupancy: string;
  active_session_id: string | null;
  pending_qr_count: number;
  qr_token: string | null;
};

export type OrderItem = {
  id: string;
  menu_item_id: string | null;
  item_name_snapshot: string;
  quantity: number;
  unit_price_minor: number;
  tax_minor: number;
  line_total_minor: number;
  currency_code: string;
  special_instructions: string;
};

export type Order = {
  id: string;
  table_id: string;
  dining_session_id: string | null;
  source: string;
  status: string;
  customer_note: string;
  submitted_at: string;
  accepted_at: string | null;
  rejected_at: string | null;
  rejection_reason_code: string | null;
  rejection_note: string;
  version: number;
  claim_state: string;
  claimed_by_membership_id: string | null;
  claimed_at: string | null;
  claim_timeout_at: string | null;
  escalated_by_membership_id: string | null;
  escalated_at: string | null;
  items: OrderItem[];
  subtotal_minor: number;
  tax_minor: number;
  total_minor: number;
  currency_code: string;
};

export type OrderSource = "QR" | "WAITER" | "PHONE" | "MANAGER";

/* Kitchen */ export type KitchenTicketItem = {
  id: string;
  order_item_id: string;
  status: string;
  quantity_snapshot: number;
  instructions_snapshot: string;
  item_name: string | null;
  table_display_name: string | null;
};

export type KitchenTicket = {
  id: string;
  order_id: string;
  ticket_number: number;
  status: string;
  created_at: string;
  started_at: string | null;
  ready_at: string | null;
  table_display_name: string | null;
  items: KitchenTicketItem[];
};

/* -------------------------------------------------------------------------
   Billing / Payments
   ------------------------------------------------------------------------- */

export type PaymentLink = {
  id: string;
  url: string;
  expires_at: string | null;
  max_uses: number | null;
  used_count: number;
  code?: string;
};

export type RefundRequest = {
  id: string;
  bill_id: string;
  amount_minor: number;
  reason?: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  created_at: string;
  processed_at: string | null;
};

export type VoidPaymentRequest = {
  payment_id: string;
  reason?: string;
};

export type RecordPaymentRequest = {
  method_id: string;
  amount_minor: number;
  note?: string;
};

/* -------------------------------------------------------------------------
   Plan 11 — Inventory & Stock Management
   ------------------------------------------------------------------------- */

export type Ingredient = {
  id: string;
  name: string;
  description?: string;
  current_stock: number;
  minimum_stock: number;
  unit: string;
  low_stock_alert: boolean;
  supplier_id?: string;
  category?: string;
  recipe_ids?: string[];
};

export type Supplier = {
  id: string;
  name: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  rating: number;
  lead_days: number;
  is_active: boolean;
  created_at: string;
};

export type PurchaseOrder = {
  id: string;
  supplier_id: string;
  status: "DRAFT" | "SUBMITTED" | "RECEIVED" | "CANCELLED";
  items: PurchaseOrderItem[];
  total_minor: number;
  created_at: string;
  updated_at: string;
  expected_delivery?: string;
};

export type PurchaseOrderItem = {
  id: string;
  ingredient_id: string;
  quantity_ordered: number;
  unit_price_minor: number;
  line_total_minor: number;
};

export type StockMovement = {
  id: string;
  ingredient_id: string;
  movement_type: "RECEIVE" | "ADJUST" | "DEDUCT" | "WASTE";
  quantity: number;
  previous_stock: number;
  new_stock: number;
  reason?: string;
  performed_by_membership_id: string;
  created_at: string;
};

export type RecipeIngredient = {
  id: string;
  ingredient_id: string;
  quantity_minor: number;
  ingredient_name: string;
};

/* -------------------------------------------------------------------------
   Plan 12 — Multi-Branch Management
   ------------------------------------------------------------------------- */

export type Branch = {
  id: string;
  name: string;
  code?: string;
  address?: string;
  phone?: string;
  timezone: string;
  currency_code: string;
  is_active: boolean;
  opening_hours?: string;
  settings_json: string;
  owner_membership_id?: string;
  restaurant_name?: string;
  manager_name?: string;
};

export type BranchTable = {
  id: string;
  table_code: string;
  display_name: string;
  seating_capacity?: number;
  status: string;
  qr_code_active: boolean;
};

export type BranchManager = {
  id: string;
  branch_id: string;
  membership_id: string;
  role: string;
  is_active: boolean;
  assigned_at: string;
};

export type BranchSalesReport = {
  id: string;
  report_date: string;
  total_sales_minor: number;
  total_sales_display: string;
  total_orders: number;
  total_orders_completed: number;
  total_orders_pending: number;
  total_revenue_minor: number;
  total_revenue_display: string;
  average_ticket_minor: number;
  payment_breakdown: Record<string, number>;
  created_at: string;
};

export type BranchDashboardSummary = {
  id: string;
  summary_date: string;
  total_revenue_minor: number;
  total_revenue_display: string;
  total_orders: number;
  average_rating?: number | null;
  low_stock_count: number;
  active_tables: number;
};

export type OwnerDashboardSummary = {
  restaurant_name: string;
  total_revenue_minor: number;
  total_revenue_display: string;
  total_orders: number;
  branch_count: number;
  active_branch_count: number;
  branches: BranchDashboardSummary[];
};

/* -------------------------------------------------------------------------
   Plan 13 — Employees & Shifts
   ------------------------------------------------------------------------- */

export type Employee = {
  id: string;
  membership_id: string;
  role: string;
  name: string;
  email: string;
  phone?: string;
  is_active: boolean;
  hired_at: string;
  branch_id?: string;
};

export type Shift = {
  id: string;
  employee_id: string;
  branch_id: string;
  date: string;
  start_time: string;
  end_time: string;
  status: "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "NO_SHOW";
  notes?: string;
};

export type ShiftAssignment = {
  id: string;
  shift_id: string;
  employee_id: string;
  assigned_by_membership_id: string;
  accepted_by_employee: boolean;
  accepted_at: string | null;
};

/* -------------------------------------------------------------------------
   Plan 14 — Loyalty & Coupons
   ------------------------------------------------------------------------- */

export type LoyaltyAccount = {
  id: string;
  membership_id: string;
  points_balance: number;
  total_earned: number;
  total_redeemed: number;
  lifetime_spend_minor: number;
  tier: "STANDARD" | "SILVER" | "GOLD" | "PLATINUM";
  last_earned_at?: string;
  last_redeemed_at?: string;
};

export type LoyaltyTransaction = {
  id: string;
  membership_id: string;
  type: "EARN" | "REDEEM";
  points: number;
  reason: string;
  reference_id: string; // order_id or coupon_id
  created_at: string;
};

export type Coupon = {
  id: string;
  code: string;
  name: string;
  description?: string;
  discount_type: "PERCENT" | "FIXED";
  discount_value: number;
  minimum_spend_minor: number;
  maximum_redeem_count: number | null;
  current_redeem_count: number;
  is_active: boolean;
  valid_from: string;
  valid_until: string | null;
  usage_limit_per_customer: number | null;
};

export type CouponRedemption = {
  id: string;
  coupon_id: string;
  membership_id: string;
  order_id: string;
  discount_amount_minor: number;
  redeemed_at: string;
};

/* -------------------------------------------------------------------------
   Plan 15 — Reviews & Ratings
   ------------------------------------------------------------------------- */

export type Review = {
  id: string;
  restaurant_id: string;
  membership_id?: string; // null = anonymous
  rating: number; // 1-5
  title?: string;
  content?: string;
  images?: string[]; // image paths/URLs
  status: "PENDING" | "APPROVED" | "REJECTED";
  created_at: string;
  responded_at?: string;
  response_text?: string;
};

export type ReviewResponse = {
  review_id: string;
  response_text: string;
  responded_at: string;
};

export type ReviewsSummary = {
  average_rating: number;
  total_reviews: number;
  rating_distribution: { rating: number; count: number }[];
};

/* -------------------------------------------------------------------------
   Plan 16 — Subscriptions & Trials
   ------------------------------------------------------------------------- */

export type SubscriptionPlan = {
  id: string;
  name: string;
  description?: string;
  price_minor: number;
  billing_interval: "MONTHLY" | "QUARTERLY" | "ANNUAL";
  trial_days: number;
  features: string[];
  is_active: boolean;
};

export type Subscription = {
  id: string;
  membership_id: string;
  plan_id: string;
  status: "TRIAL" | "ACTIVE" | "PAST_DUE" | "CANCELLED";
  started_at: string;
  billing_cycle_end: string;
  cancel_at_period_end: boolean;
  canceled_at?: string;
};

export type SubscriptionBillingInfo = {
  id: string;
  subscription_id: string;
  amount_minor: number;
  currency_code: string;
  billing_date: string;
  status: "SCHEDULED" | "PAID" | "FAILED";
};

/* -------------------------------------------------------------------------
   Plan 11 — Inventory & Stock Management (duplicate section - remove)
   ------------------------------------------------------------------------- */

 /* -------------------------------------------------------------------------
   Helpers
   ------------------------------------------------------------------------- */

export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `idemp-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function formatMoney(amountMinor: number, currency = "USD"): string {
  const value = amountMinor / 100;
  try {
    return new Intl.NumberFormat(currency === "NPR" ? "en-IN" : "en-US", {
      style: "currency",
      currency,
      currencyDisplay: currency === "NPR" ? "narrowSymbol" : undefined,
    }).format(value);
  } catch {
    return `${currency} ${value.toFixed(2)}`;
  }
}

/* -------------------------------------------------------------------------
   API endpoint URLs (helpers)
   ------------------------------------------------------------------------- */

export type BranchApiPaths = {
  branches: () => string;
  branch: (id: string) => string;
  tables: (branchId: string) => string;
  table: (branchId: string, tableId: string) => string;
  managers: (branchId: string) => string;
  assignManager: (branchId: string, membershipId: string) => string;
  dashboardSummary: (branchId: string) => string;
};

export type EmployeeApiPaths = {
  employees: (branchId?: string) => string;
  employee: (id: string) => string;
  shifts: (branchId: string, date: string) => string;
  assignShift: (shiftId: string, employeeId: string, membershipId: string) => string;
};

export type LoyaltyApiPaths = {
  loyaltyAccount: (membershipId: string) => string;
  transactions: (membershipId: string) => string;
  coupons: () => string;
  redeemCoupon: (couponId: string, membershipId: string) => string;
};

export type ReviewApiPaths = {
  reviews: (restaurantId: string) => string;
  review: (reviewId: string) => string;
  respondReview: (reviewId: string, responseText: string) => string;
};

export type SubscriptionApiPaths = {
  plans: () => string;
  subscription: (membershipId: string) => string;
  billing: (membershipId: string) => string;
};

/* -------------------------------------------------------------------------
   createApiClient — platform-neutral client factory
   ------------------------------------------------------------------------- */

export function createApiClient(config: ApiClientConfig): ApiClient {
  const defaultTimeout = config.timeoutMs ?? 15_000;

  async function request<T>(_path: string, options: ApiRequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...options.headers,
    };
    if (typeof options.body === "string" && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const token = await config.getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

    const isBrowser = typeof document !== "undefined";
    if (!isBrowser && (options.method ?? "GET").toUpperCase() === "GET") {
      headers["Cache-Control"] = "no-cache";
    }

    const controller = new AbortController();
    const timeoutMs = options.timeoutMs ?? defaultTimeout;
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    const onCallerAbort = () => controller.abort();
    options.signal?.addEventListener("abort", onCallerAbort);

    try {
      throw new Error("Platform-specific fetch required");
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (timedOut) {
        throw new ApiTransportError("timeout", "The server did not respond in time.");
      }
      throw new ApiTransportError("offline", "Could not reach the server.");
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener("abort", onCallerAbort);
    }
  }

  async function authHeaders(): Promise<Record<string, string>> {
    const token = await config.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  return {
    request,
    authHeaders,
    url: (path: string) => {
      const base = config.baseUrl.replace(/\/+$/, "");
      const suffix = path.startsWith("/") ? path : `/${path}`;
      return `${base}${suffix}`;
    },
  };
}

/* -------------------------------------------------------------------------
   End of file — nothing below this line may import DOM/React Native APIs
   ------------------------------------------------------------------------- */