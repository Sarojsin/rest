import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiError, type LoginResponse, type MFAChallengeResponse, type Me } from "@rest/api-client";

import { api, setSessionExpiredHandler } from "./api";
import { queryClient } from "./query";
import { getAccessToken, getRefreshToken, setTokens } from "./tokenStore";
import { registerDeviceToken, unregisterDeviceToken } from "./fcm";

/**
 * `offline` is a distinct state on purpose: a cached token that we could not
 * verify is not the same as a valid session, and the app must not show order or
 * bill data it cannot prove is current.
 */
export type AuthStatus = "loading" | "anonymous" | "authenticated" | "offline" | "mfa_required";

type AuthState = {
  status: AuthStatus;
  me: Me | null;
  /** True when the previous session ended with a 401, not a deliberate sign-out. */
  sessionExpired: boolean;
  /** MFA challenge data when status is "mfa_required" */
  mfaChallenge: MFAChallengeResponse | null;
  signIn: (email: string, password: string) => Promise<Me | { mfaRequired: true; mfaToken: string }>;
  completeMfa: (mfaToken: string, mfaCode?: string, recoveryCode?: string) => Promise<Me>;
  signOut: () => Promise<void>;
  retryBootstrap: () => void;
  /** Switch to a different membership (and optionally branch). Returns new Me. */
  switchMembership: (membershipId: string, branchId?: string) => Promise<Me>;
  has: (permission: string) => boolean;
  hasAny: (permissions: string[]) => boolean;
  /** Get the active restaurant ID (uses branch context if set) */
  getRestaurantId: () => string | null;
  /** Get the active branch ID if set */
  getBranchId: () => string | null;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [me, setMe] = useState<Me | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [mfaChallenge, setMfaChallenge] = useState<MFAChallengeResponse | null>(null);
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
      setMfaChallenge(null);
      setStatus("anonymous");
      setSessionExpired(true);
    });
    return () => setSessionExpiredHandler(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    void (async () => {
      const [accessToken, refreshToken] = await Promise.all([
        getAccessToken(),
        getRefreshToken(),
      ]);
      // A refresh token alone still means a session we can restore.
      if (!accessToken && !refreshToken) {
        if (!cancelled) {
          setMe(null);
          setMfaChallenge(null);
          setStatus("anonymous");
        }
        return;
      }
      try {
        const current = await api<Me>("/api/v1/me");
        if (cancelled) return;
        setMe(current);
        setMfaChallenge(null);
        setStatus("authenticated");
        // Register this device for FCM push notifications (fire-and-forget).
        void registerDeviceToken();
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          // A 401 here means the refresh attempt already failed; lib/api.ts
          // cleared the tokens and notified the provider.
          setMe(null);
          setMfaChallenge(null);
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
    const result = await api<LoginResponse | MFAChallengeResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: email.trim(), password }),
    });

    // Check if MFA is required
    if ("mfa_required" in result && result.mfa_required) {
      const mfaResult = result as MFAChallengeResponse;
      setMfaChallenge(mfaResult);
      setStatus("mfa_required");
      return { mfaRequired: true as const, mfaToken: mfaResult.mfa_token };
    }

    // Normal login success
    const loginResult = result as LoginResponse;
    await setTokens(loginResult.access_token, loginResult.refresh_token);
    // Anything cached belongs to a previous staff member.
    queryClient.clear();
    setSessionExpired(false);
    setMfaChallenge(null);
    setMe(loginResult.user);
    setStatus("authenticated");
    // Register this device for FCM push notifications (fire-and-forget).
    void registerDeviceToken();
    return loginResult.user;
  }, []);

  const completeMfa = useCallback(async (mfaToken: string, mfaCode?: string, recoveryCode?: string) => {
    const result = await api<LoginResponse>("/api/v1/auth/mfa/challenge", {
      method: "POST",
      body: JSON.stringify({ mfa_token: mfaToken, mfa_code: mfaCode, recovery_code: recoveryCode }),
    });
    await setTokens(result.access_token, result.refresh_token);
    queryClient.clear();
    setSessionExpired(false);
    setMfaChallenge(null);
    setMe(result.user);
    setStatus("authenticated");
    // Register this device for FCM push notifications (fire-and-forget).
    void registerDeviceToken();
    return result.user;
  }, []);

  const switchMembership = useCallback(async (membershipId: string, branchId?: string) => {
    const result = await api<LoginResponse>("/api/v1/auth/switch-membership", {
      method: "POST",
      body: JSON.stringify({ membership_id: membershipId, branch_id: branchId }),
    });
    await setTokens(result.access_token, result.refresh_token);
    queryClient.clear();
    setSessionExpired(false);
    setMe(result.user);
    setStatus("authenticated");
    // Register this device for FCM push notifications (fire-and-forget).
    void registerDeviceToken();
    return result.user;
  }, []);

  const signOut = useCallback(async () => {
    // Clear the device token so this phone stops receiving pushes for this user.
    void unregisterDeviceToken();
    await setTokens(null, null);
    queryClient.clear();
    setSessionExpired(false);
    setMfaChallenge(null);
    setMe(null);
    setStatus("anonymous");
  }, []);

  const retryBootstrap = useCallback(() => {
    setBootstrapNonce((value) => value + 1);
  }, []);

  const value = useMemo<AuthState>(() => {
    const permissions = me?.membership.permissions ?? [];
    const getRestaurantId = () => me?.membership?.restaurant_id ?? null;
    const getBranchId = () => me?.active_branch_id ?? null;
    return {
      status,
      me,
      sessionExpired,
      mfaChallenge,
      signIn,
      completeMfa,
      signOut,
      switchMembership,
      retryBootstrap,
      has: (permission: string) => permissions.includes(permission),
      hasAny: (list: string[]) => list.some((permission) => permissions.includes(permission)),
      getRestaurantId,
      getBranchId,
    };
  }, [status, me, sessionExpired, mfaChallenge, signIn, completeMfa, signOut, switchMembership, retryBootstrap]);

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
 *
 * Fixed to handle ALL roles properly with fallback to ensure no user is
 * left without a valid destination after login.
 */
export function homeRouteFor(permissions: string[]): "/waiter" | "/kitchen" | "/cashier" | "/" | null {
  // Waiter: has orders.create (waiter, manager, owner)
  if (permissions.includes("orders.create")) return "/waiter";
  // Kitchen: has kitchen.update (kitchen, manager, owner)
  if (permissions.includes("kitchen.update")) return "/kitchen";
  // Cashier: has bills.issue (cashier, manager, owner)
  if (permissions.includes("bills.issue")) return "/cashier";
  // Fallback: any role with orders.read goes to waiter (tables screen)
  // This ensures ALL authenticated users with basic read access get a valid screen
  if (permissions.includes("orders.read")) return "/waiter";
  return null;
}
