/**
 * Platform (Super Admin) API client.
 *
 * Differences from the tenant client, by design:
 * - no token state and no storage access: the browser holds HttpOnly cookies;
 * - `credentials: "include"` on every request;
 * - the only JS-readable value is the non-secret `platform_csrf` cookie, sent
 *   as `X-CSRF-Token` on every non-GET request;
 * - a 401 `TOKEN_EXPIRED` refreshes once and retries once;
 * - a 401 `STEP_UP_REQUIRED` dispatches an event instead of logging out.
 *
 * Nothing here writes to localStorage/sessionStorage or logs credentials.
 */

export type PlatformProblem = {
  title?: string;
  status?: number;
  code?: string;
  detail?: string;
  request_id?: string;
  details?: Record<string, unknown>;
};

export class PlatformApiError extends Error {
  status: number;
  code: string;
  detail: string;
  requestId: string | null;
  details: Record<string, unknown> | undefined;

  constructor(status: number, code: string, detail: string, problem: PlatformProblem = {}) {
    super(detail);
    this.name = "PlatformApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.requestId = problem.request_id ?? null;
    this.details = problem.details;
  }
}

export const STEP_UP_EVENT = "platform:step-up-required";

const API_BASE = (import.meta.env.VITE_PLATFORM_API_URL ?? "").replace(/\/+$/, "");

function absoluteUrl(path: string): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${suffix}`;
}

// Cross-origin SPAs cannot read cookies set for the API host via document.cookie.
// We keep the latest CSRF token in memory (from auth responses) and fall back to
// the cookie for same-origin setups.
let platformCsrfToken: string | null = null;

export function setPlatformCsrfToken(token: string | null | undefined): void {
  if (token) platformCsrfToken = token;
}

export function clearPlatformCsrfToken(): void {
  platformCsrfToken = null;
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

function getPlatformCsrfToken(): string | null {
  return platformCsrfToken || readCookie("platform_csrf");
}

async function readProblem(response: Response): Promise<PlatformProblem> {
  try {
    const contentType = response.headers.get("content-type") ?? "";
    // Platform problems are RFC 7807 `application/problem+json`.
    if (!contentType.includes("json")) return {};
    const parsed: unknown = await response.json();
    return parsed && typeof parsed === "object" ? (parsed as PlatformProblem) : {};
  } catch {
    return {};
  }
}

function isSafeMethod(method: string): boolean {
  return ["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
}

export type PlatformRequestOptions = {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  /** Internal: prevents infinite refresh loops. */
  retried?: boolean;
};

async function send(path: string, options: PlatformRequestOptions): Promise<Response> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...options.headers,
  };
  if (options.body !== undefined && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (!isSafeMethod(method)) {
    const csrf = getPlatformCsrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  return fetch(absoluteUrl(path), {
    method,
    headers,
    credentials: "include",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
}

let refreshInFlight: Promise<boolean> | null = null;

/** Single-flight refresh so parallel 401s do not rotate the family twice. */
export function refreshPlatformSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const response = await send("/api/platform/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (response.ok) {
        const contentType = response.headers.get("content-type") ?? "";
        if (contentType.includes("application/json")) {
          try {
            const parsed = (await response.clone().json()) as { csrf_token?: string | null };
            if (parsed?.csrf_token) setPlatformCsrfToken(parsed.csrf_token);
          } catch {
            // ignore parse errors; cookie-based flow may still work
          }
        }
      }
      return response.ok;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export async function platformFetch<T>(
  path: string,
  options: PlatformRequestOptions = {}
): Promise<T> {
  const response = await send(path, options);

  if (response.status === 401 && !options.retried) {
    const problem = await readProblem(response);
    if (problem.code === "TOKEN_EXPIRED") {
      const refreshed = await refreshPlatformSession();
      if (refreshed) {
        return platformFetch<T>(path, { ...options, retried: true });
      }
    }
    if (problem.code === "STEP_UP_REQUIRED") {
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent(STEP_UP_EVENT, { detail: problem.details ?? {} })
        );
      }
      throw new PlatformApiError(401, problem.code, problem.detail ?? "Re-authenticate to continue.", problem);
    }
    throw new PlatformApiError(401, problem.code ?? "AUTH_REQUIRED", problem.detail ?? "Authentication is required.", problem);
  }

  if (!response.ok) {
    const problem = await readProblem(response);
    throw new PlatformApiError(
      response.status,
      problem.code ?? `HTTP_${response.status}`,
      problem.detail ?? problem.title ?? response.statusText ?? "Request failed.",
      problem
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return (await response.text()) as unknown as T;
  }
  const data = (await response.json()) as T;
  if (data && typeof data === "object" && "csrf_token" in (data as Record<string, unknown>)) {
    const token = (data as { csrf_token?: string | null }).csrf_token;
    if (typeof token === "string" && token) setPlatformCsrfToken(token);
  }
  return data;
}

/* -------------------------------------------------------------------------
   Auth types — mirror app/modules/platform/schemas.py
   ------------------------------------------------------------------------- */

export type PlatformAdmin = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  mfa_enabled: boolean;
};

export type PlatformMe = PlatformAdmin & { permissions: string[] };

export type LoginChallenge = {
  mfa_required: boolean;
  enrollment_required: boolean;
  ticket: string;
  expires_in: number;
};

export type AuthSuccess = {
  admin: PlatformAdmin;
  expires_in: number;
  recovery_codes?: string[] | null;
  csrf_token?: string | null;
};

export type MfaEnrollment = {
  secret: string;
  provisioning_uri: string;
  issuer: string;
};

export type PlatformSession = {
  family_id: string;
  created_at: string;
  expires_at: string;
  ip: string | null;
  user_agent: string | null;
  current: boolean;
};
