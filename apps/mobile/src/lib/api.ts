import { createApiClient } from "@rest/api-client";
import { API_BASE_URL } from "./config";
import { getAccessToken, getRefreshToken, setTokens } from "./tokenStore";

export * from "@rest/api-client";

let sessionExpiredHandler: (() => void) | null = null;
let refreshPromise: Promise<string | null> | null = null;

/**
 * Registered by the auth provider so a 401 anywhere in the app drops the
 * session exactly once, instead of every screen inventing its own handling.
 */
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  sessionExpiredHandler = handler;
}

/** Treat a token that expires within this window as already stale. */
const EXPIRY_SKEW_MS = 30_000;

/** Reads the `exp` claim without pulling in a JWT library. */
function isExpired(token: string): boolean {
  const payload = token.split(".")[1];
  if (!payload) return false;
  try {
    // Hermes exposes `atob`; if it ever does not, let the API reject the token.
    if (typeof atob !== "function") return false;
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const claims = JSON.parse(atob(padded)) as { exp?: number };
    if (typeof claims.exp !== "number") return false;
    return claims.exp * 1_000 <= Date.now() + EXPIRY_SKEW_MS;
  } catch {
    // A token we cannot parse is left to the API to reject.
    return false;
  }
}

async function performRefresh(): Promise<string | null> {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return null;
    }

    const data = (await response.json()) as {
      access_token: string;
      refresh_token: string;
    };
    await setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    return null;
  }
}

/**
 * Exactly one refresh at a time.
 *
 * The backend rotates and consumes refresh tokens, so two concurrent refreshes
 * would fail the second one and sign the user out mid-session. Every caller —
 * proactive expiry checks and 401 handling — shares this promise.
 */
function refreshTokens(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = performRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function getValidAccessToken(): Promise<string | null> {
  const accessToken = await getAccessToken();
  if (accessToken && !isExpired(accessToken)) return accessToken;
  return refreshTokens();
}

const client = createApiClient({
  baseUrl: API_BASE_URL,
  getToken: getValidAccessToken,
  onUnauthorized: async () => {
    // The API client retries the rejected request once when this succeeds.
    const newToken = await refreshTokens();
    if (!newToken) {
      await setTokens(null, null);
      sessionExpiredHandler?.();
    }
  },
});

export const api = client.request;
export const apiUrl = client.url;
export const apiAuthHeaders = client.authHeaders;
