import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  PlatformApiError,
  platformFetch,
  refreshPlatformSession,
  type AuthSuccess,
  type LoginChallenge,
  type MfaEnrollment,
  type PlatformMe,
} from "./platformApi";

type PlatformAuthState = {
  admin: PlatformMe | null;
  loading: boolean;
  error: string | null;
  /** Login challenge lives in component memory only; a reload restarts login. */
  challenge: LoginChallenge | null;
  login: (email: string, password: string) => Promise<LoginChallenge>;
  verifyMfa: (code: string) => Promise<AuthSuccess>;
  startEnrollment: () => Promise<MfaEnrollment>;
  verifyEnrollment: (code: string) => Promise<string[] | null>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
  has: (permission: string) => boolean;
  clearChallenge: () => void;
};

const PlatformAuthContext = createContext<PlatformAuthState | null>(null);

export function describePlatformError(error: unknown): string {
  if (error instanceof PlatformApiError) {
    if (error.code === "CSRF_INVALID" || error.code === "ORIGIN_INVALID") {
      return "The request could not be verified. Reload the page and try again.";
    }
    if (error.code === "INVALID_CREDENTIALS") return "Email or password is incorrect.";
    if (error.code === "ACCOUNT_DISABLED") return "This account is disabled.";
    if (error.code === "MFA_INVALID") return "That code is not valid.";
    if (error.code === "TICKET_EXPIRED" || error.code === "INVALID_TICKET") {
      return "This sign-in attempt expired. Start again.";
    }
    if (error.code === "TOKEN_REUSE" || error.code === "TOKEN_REVOKED") {
      return "Your session is no longer valid. Sign in again.";
    }
    return error.detail;
  }
  return "Something went wrong. Try again.";
}

export function PlatformAuthProvider({ children }: { children: React.ReactNode }) {
  const [admin, setAdmin] = useState<PlatformMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null);

  const loadMe = useCallback(async (): Promise<PlatformMe> => {
    const me = await platformFetch<PlatformMe>("/api/platform/auth/me");
    setAdmin(me);
    return me;
  }, []);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await loadMe();
    } catch {
      setAdmin(null);
    } finally {
      setLoading(false);
    }
  }, [loadMe]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const me = await platformFetch<PlatformMe>("/api/platform/auth/me");
        if (!cancelled) setAdmin(me);
      } catch (err) {
        if (err instanceof PlatformApiError && err.status === 401) {
          // Recover an existing refresh cookie on a fresh page load.
          const refreshed = await refreshPlatformSession();
          if (refreshed) {
            try {
              const me = await platformFetch<PlatformMe>("/api/platform/auth/me");
              if (!cancelled) setAdmin(me);
            } catch {
              if (!cancelled) setAdmin(null);
            }
          } else if (!cancelled) {
            setAdmin(null);
          }
        } else if (!cancelled) {
          setError(describePlatformError(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    const result = await platformFetch<LoginChallenge>("/api/platform/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setChallenge(result);
    return result;
  }, []);

  const verifyMfa = useCallback(
    async (code: string) => {
      if (!challenge) throw new Error("No sign-in challenge in progress.");
      const result = await platformFetch<AuthSuccess>("/api/platform/auth/mfa/verify", {
        method: "POST",
        body: { ticket: challenge.ticket, code },
      });
      setChallenge(null);
      await loadMe();
      return result;
    },
    [challenge, loadMe]
  );

  const startEnrollment = useCallback(async () => {
    if (!challenge) throw new Error("No sign-in challenge in progress.");
    return platformFetch<MfaEnrollment>("/api/platform/auth/mfa/enroll/start", {
      method: "POST",
      body: { ticket: challenge.ticket },
    });
  }, [challenge]);

  const verifyEnrollment = useCallback(
    async (code: string) => {
      if (!challenge) throw new Error("No sign-in challenge in progress.");
      const result = await platformFetch<AuthSuccess>(
        "/api/platform/auth/mfa/enroll/verify",
        {
          method: "POST",
          body: { ticket: challenge.ticket, code },
        }
      );
      setChallenge(null);
      await loadMe();
      return result.recovery_codes ?? null;
    },
    [challenge, loadMe]
  );

  const logout = useCallback(async () => {
    try {
      await platformFetch<void>("/api/platform/auth/logout", { method: "POST" });
    } catch {
      // Server-side session may already be gone; local state is still cleared.
    }
    setAdmin(null);
    setChallenge(null);
    setError(null);
  }, []);

  const value = useMemo<PlatformAuthState>(
    () => ({
      admin,
      loading,
      error,
      challenge,
      login,
      verifyMfa,
      startEnrollment,
      verifyEnrollment,
      logout,
      reload,
      has: (permission: string) => Boolean(admin?.permissions.includes(permission)),
      clearChallenge: () => setChallenge(null),
    }),
    [
      admin,
      loading,
      error,
      challenge,
      login,
      verifyMfa,
      startEnrollment,
      verifyEnrollment,
      logout,
      reload,
    ]
  );

  return (
    <PlatformAuthContext.Provider value={value}>{children}</PlatformAuthContext.Provider>
  );
}

export function usePlatformAuth(): PlatformAuthState {
  const context = useContext(PlatformAuthContext);
  if (context === null) {
    throw new Error("usePlatformAuth must be used inside PlatformAuthProvider");
  }
  return context;
}
