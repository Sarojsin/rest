import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, getToken, setToken, type Me } from "./api";

type AuthState = {
  me: Me | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<Me>;
  logout: () => void;
  has: (permission: string) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiFetch<Me>("/api/v1/me")
      .then(setMe)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      me,
      loading,
      error,
      async login(email: string, password: string) {
        setError(null);
        const result = await apiFetch<{ access_token: string; user: Me }>("/api/v1/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        setToken(result.access_token);
        setMe(result.user);
        return result.user;
      },
      logout() {
        setToken(null);
        setMe(null);
      },
      has(permission: string) {
        return Boolean(me?.membership.permissions.includes(permission));
      },
    }),
    [me, loading, error]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
