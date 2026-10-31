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
};

const DEFAULT_TIMEOUT_MS = 15_000;

function joinUrl(baseUrl: string, path: string): string {
  const base = baseUrl.replace(/\/+$/, "");
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${base}${suffix}`;
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as Problem;
    return new ApiError(
      response.status,
      body.code ?? "HTTP_ERROR",
      body.detail ?? body.title ?? "Request failed"
    );
  } catch {
    return new ApiError(response.status, "HTTP_ERROR", "Request failed");
  }
}

export function createApiClient(config: ApiClientConfig): ApiClient {
  const defaultTimeout = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
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

    // Browsers must not serve a cached GET: prices, availability and order
    // state have to be fresh or the kitchen and the customer disagree.
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
      const response = await fetch(joinUrl(config.baseUrl, path), {
        method: options.method ?? "GET",
        headers,
        body: options.body,
        signal: controller.signal,
        ...(isBrowser ? { cache: "no-store" as RequestCache } : {}),
      });

      if (response.status === 401 && token) {
        config.onUnauthorized?.();
      }
      if (!response.ok) {
        throw await parseError(response);
      }
      if (response.status === 204) {
        return undefined as T;
      }
      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (timedOut) {
        throw new ApiTransportError("timeout", "The server did not respond in time.");
      }
      if (options.signal?.aborted) {
        throw new ApiTransportError("aborted", "Request cancelled.");
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
    url: (path: string) => joinUrl(config.baseUrl, path),
  };
}

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
   Response types (mirror the FastAPI contracts in docs/api-contracts.md)
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

/**
 * `POST /auth/login`. There is no refresh endpoint yet: the access token is
 * valid for one shift (`access_token_minutes = 480`).
 */
export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: Me;
};

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
  items: OrderItem[];
  subtotal_minor: number;
  tax_minor: number;
  total_minor: number;
  currency_code: string;
};

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

export type KitchenTicketItem = {
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

export type BillItem = {
  id: string;
  description_snapshot: string;
  quantity: number;
  unit_price_minor: number;
  tax_minor: number;
  line_total_minor: number;
};

export type Payment = {
  id: string;
  method: string;
  status: string;
  amount_minor: number;
  currency_code: string;
  note: string;
  created_at: string;
  succeeded_at: string | null;
};

export type PaymentMethodConfig = {
  id: string;
  label: string;
  kind: string; // "CASH" | "QR"
  account_hint: string;
  instructions: string;
  is_active: boolean;
  display_order: number;
  has_qr_image: boolean;
  qr_image_url: string | null;
};

export type Bill = {
  id: string;
  dining_session_id: string;
  status: string;
  currency_code: string;
  subtotal_minor: number;
  tax_minor: number;
  total_minor: number;
  paid_minor: number;
  balance_due_minor: number;
  version: number;
  issued_at: string | null;
  items: BillItem[];
  payments: Payment[];
};

export type SalesReport = {
  currency_code: string;
  order_count: number;
  accepted_order_count: number;
  cancelled_order_count: number;
  gross_sales_minor: number;
  tax_minor: number;
  collected_minor: number;
  outstanding_minor: number;
  top_items: { name: string; quantity: number; sales_minor: number }[];
};

export type AuditEvent = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  occurred_at: string;
  detail: string;
};

export type PublicOrderStatus = {
  order_id: string;
  status: string;
  restaurant_name: string;
  table_display_name: string;
  submitted_at: string;
  accepted_at: string | null;
  rejected_at: string | null;
  rejection_note: string;
  items: { name: string; quantity: number; line_total_minor: number }[];
  total_minor: number;
  currency_code: string;
};

export type PublicServiceCall = {
  id: string;
  status: string;
  requested_at: string;
  acknowledged_at: string | null;
  deduplicated: boolean;
};

export type ServiceCall = {
  id: string;
  kind: string; // "GUEST" (customer signal) | "KITCHEN" (food ready for pickup)
  table_id: string;
  table_display_name: string;
  ticket_number: number | null;
  items_summary: string;
  status: string;
  requested_at: string;
  acknowledged_at: string | null;
};
