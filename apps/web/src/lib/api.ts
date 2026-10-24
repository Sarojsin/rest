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
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

const TOKEN_KEY = "harbor.access_token";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `idemp-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function formatMoney(amountMinor: number, currency = "USD"): string {
  const value = amountMinor / 100;
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
  } catch {
    return `${currency} ${value.toFixed(2)}`;
  }
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

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { idempotencyKey?: string } = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);

  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

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

export type MenuItem = {
  id: string;
  name: string;
  description: string;
  current_price_minor: number;
  currency_code: string;
  status: string;
  display_order: number;
  image_emoji: string;
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
  created_at: string;
  succeeded_at: string | null;
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
  table_display_name: string;
  submitted_at: string;
  accepted_at: string | null;
  rejected_at: string | null;
  rejection_note: string;
  items: { name: string; quantity: number; line_total_minor: number }[];
  total_minor: number;
  currency_code: string;
};
