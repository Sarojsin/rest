/**
 * Browser adapter for the shared API client.
 *
 * Types and request behaviour live in `@rest/api-client` so the website and the
 * React Native staff app cannot drift apart. Only the token storage and the
 * same-origin base URL are platform-specific.
 */
import { createApiClient } from "@rest/api-client";

export * from "@rest/api-client";

const TOKEN_KEY = "rest.access_token";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

const client = createApiClient({
  // Same origin: Vite proxies /api and /health to the FastAPI service.
  baseUrl: "",
  getToken,
});

export const apiFetch = client.request;
