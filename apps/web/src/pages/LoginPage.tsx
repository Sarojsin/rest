import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

const DEMO_ROLES = [
  { role: "Owner", email: "owner@harbor.example" },
  { role: "Manager", email: "manager@harbor.example" },
  { role: "Waiter", email: "waiter@harbor.example" },
  { role: "Kitchen", email: "kitchen@harbor.example" },
  { role: "Cashier", email: "cashier@harbor.example" },
];

function landingFor(role: string): string {
  if (role === "kitchen") return "/staff/kitchen";
  if (role === "cashier") return "/staff/cashier";
  if (role === "owner" || role === "manager") return "/staff";
  return "/staff/tables";
}

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(() => params.get("email") ?? "waiter@harbor.example");
  const [password, setPassword] = useState(() => params.get("password") ?? "HarborWaiter!1");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await login(email, password);
      navigate(landingFor(me.membership.role));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page" data-theme="management">
      <div className="shell" style={{ width: "100%" }}>
        <header className="topbar">
          <Link className="brand" to="/">
            <div className="mark">HT</div>
            <div>
              <h1>Harbor Table</h1>
              <p>Staff access</p>
            </div>
          </Link>
          <Link className="btn ghost" to="/">
            Guest site
          </Link>
        </header>

        <form className="card login-card" onSubmit={onSubmit}>
          <p className="kicker">Staff sign in</p>
          <h2>Welcome back</h2>
          <p className="muted">
            Role permissions are enforced by the API, not by this screen. Kitchen and cashier land on
            their own stations.
          </p>

          {error ? (
            <div className="error" role="alert">
              {error}
            </div>
          ) : null}

          <label className="field">
            Email
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              autoComplete="username"
              required
            />
          </label>
          <label className="field">
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
              required
              minLength={8}
            />
          </label>
          <button className="btn btn-lg btn-block" disabled={busy} type="submit">
            {busy ? "Signing in…" : "Sign in"}
          </button>

          <div className="login-demo">
            <p className="field-hint">
              Demo accounts — tap to fill. Password pattern: Harbor&lt;Role&gt;!1
            </p>
            <div className="chip-row">
              {DEMO_ROLES.map((account) => (
                <button
                  key={account.role}
                  type="button"
                  className="cat-chip"
                  onClick={() => {
                    setEmail(account.email);
                    setPassword(`Harbor${account.role}!1`);
                    setError(null);
                  }}
                >
                  {account.role}
                </button>
              ))}
            </div>
          </div>
        </form>

        <p className="muted text-sm" style={{ textAlign: "center" }}>
          Guests never need an account — they scan the table QR code.
        </p>
      </div>
    </div>
  );
}
