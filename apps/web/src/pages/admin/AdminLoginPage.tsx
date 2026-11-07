import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { describePlatformError, usePlatformAuth } from "../../lib/platformAuth";

export default function AdminLoginPage() {
  const { admin, login } = usePlatformAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  if (admin) return <Navigate to="/" replace />;

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigate("/mfa", { replace: true });
    } catch (err) {
      setError(describePlatformError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pf-center">
      <div className="pf-card">
        <h1>Platform Console</h1>
        <p className="sub">Super Admin sign-in. This is not the restaurant dashboard.</p>

        {error ? <div className="pf-error">{error}</div> : null}

        <form onSubmit={onSubmit}>
          <div className="pf-field">
            <label htmlFor="platform-email">Email</label>
            <input
              id="platform-email"
              type="email"
              autoComplete="username"
              autoFocus
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="pf-field">
            <label htmlFor="platform-password">Password</label>
            <input
              id="platform-password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <button type="submit" className="pf-button full" disabled={busy}>
            {busy ? "Signing in…" : "Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}


