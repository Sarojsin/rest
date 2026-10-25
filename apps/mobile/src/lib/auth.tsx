import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiError, type LoginResponse, type Me } from "@rest/api-client";

import { api, setSessionExpiredHandler } from "./api";
import { queryClient } from "./query";
import { getToken, setToken } from "./tokenStore";

/**
 * `offline` is a distinct state on purpose: a cached token that we could not
 * verify is not the same as a valid session, and the app must not show order or
 * bill data it cannot prove is current.
 */
export type AuthStatus = "loading" | "anonymous" | "authenticated" | "offline";

type AuthState = {
  status: AuthStatus;
  me: Me | null;
  /** True when the previous session ended with a 401, not a deliberate sign-out. */
  sessionExpired: boolean;
  signIn: (email: string, password: string) => Promise<Me>;
  signOut: () => Promise<void>;
  retryBootstrap: () => void;
  has: (permission: string) => boolean;
  hasAny: (permissions: string[]) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [me, setMe] = useState<Me | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [bootstrapNonce, setBootstrapNonce] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  /**
   * A 401 can arrive from any screen at any time (role revoked, token expired).
   * Clearing the session here means no screen has to handle it, and the router
   * guard sends the user to the login screen exactly once.
   */
  useEffect(() => {
    setSessionExpiredHandler(() => {
      queryClient.clear();
      setMe(null);
      setStatus("anonymous");
      setSessionExpired(true);
    });
    return () => setSessionExpiredHandler(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    void (async () => {
      const token = await getToken();
      if (!token) {
        if (!cancelled) {
          setMe(null);
          setStatus("anonymous");
        }
        return;
      }
      try {
        const current = await api<Me>("/api/v1/me");
        if (cancelled) return;
        setMe(current);
        setStatus("authenticated");
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          await setToken(null);
          setMe(null);
          setStatus("anonymous");
          return;
        }
        // Token may still be valid; we just cannot prove it right now.
        setStatus("offline");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [bootstrapNonce]);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: email.trim(), password }),
    });
    await setToken(result.access_token);
    // Anything cached belongs to a previous staff member.
    queryClient.clear();
    setSessionExpired(false);
    setMe(result.user);
    setStatus("authenticated");
    return result.user;
  }, []);

  const signOut = useCallback(async () => {
    await setToken(null);
    queryClient.clear();
    setSessionExpired(false);
    setMe(null);
    setStatus("anonymous");
  }, []);

  const retryBootstrap = useCallback(() => {
    setBootstrapNonce((value) => value + 1);
  }, []);

  const value = useMemo<AuthState>(() => {
    const permissions = me?.membership.permissions ?? [];
    return {
      status,
      me,
      sessionExpired,
      signIn,
      signOut,
      retryBootstrap,
      has: (permission: string) => permissions.includes(permission),
      hasAny: (list: string[]) => list.some((permission) => permissions.includes(permission)),
    };
  }, [status, me, sessionExpired, signIn, signOut, retryBootstrap]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/**
 * Where a signed-in member belongs. Navigation is gated on backend
 * capabilities, not role names, so a renamed or re-scoped role keeps working.
 */
export function homeRouteFor(permissions: string[]): "/waiter" | "/kitchen" | "/cashier" | null {
  if (permissions.includes("orders.create")) return "/waiter";
  if (permissions.includes("kitchen.update")) return "/kitchen";
  if (permissions.includes("bills.issue")) return "/cashier";
  return null;
}
