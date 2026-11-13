/**
 * Browser adapter for the shared API client.
 *
 * Types and request behaviour live in `@rest/api-client` so the website and the
 * React Native staff app cannot drift apart. Only the token storage and the
 * same-origin base URL are platform-specific.
 */
import { createApiClient } from "@rest/api-client";

const TOKEN_KEY = "rest.access_token";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

const client = createApiClient({
  // Same origin in dev (Vite proxies /api), or the Render backend URL in prod.
  baseUrl: import.meta.env.VITE_API_URL ?? "",
  getToken,
});

export const apiFetch = client.request;

/** Resolve an API path against the configured backend base URL. */
export function apiUrl(path: string): string {
  const base = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
  if (/^https?:\/\//i.test(path)) return path;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

/* Re-export types from the shared api-client package */
export * from "@rest/api-client";