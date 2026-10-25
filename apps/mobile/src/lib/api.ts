import { createApiClient } from "@rest/api-client";
import { API_BASE_URL } from "./config";
import { getToken, setToken } from "./tokenStore";

export * from "@rest/api-client";

let sessionExpiredHandler: (() => void) | null = null;

/**
 * Registered by the auth provider so a 401 anywhere in the app drops the
 * session exactly once, instead of every screen inventing its own handling.
 */
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  sessionExpiredHandler = handler;
}

const client = createApiClient({
  baseUrl: API_BASE_URL,
  getToken,
  onUnauthorized: () => {
    void setToken(null);
    sessionExpiredHandler?.();
  },
});

export const api = client.request;
export const apiUrl = client.url;
export const apiAuthHeaders = client.authHeaders;
