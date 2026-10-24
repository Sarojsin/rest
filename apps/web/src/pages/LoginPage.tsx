import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("waiter@harbor.example");
  const [password, setPassword] = useState("HarborWaiter!1");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await login(email, password);
      const role = me.membership.role;
      if (role === "kitchen") navigate("/staff/kitchen");
      else if (role === "cashier") navigate("/staff/cashier");
      else if (role === "owner" || role === "manager") navigate("/staff/reports");
      else navigate("/staff/tables");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <div className="mark">HT</div>
          <div>
            <h1>Harbor Table</h1>
            <p>Staff access</p>
          </div>
        </Link>
      </header>
      <form className="card login-card" onSubmit={onSubmit}>
        <div className="kicker">Staff</div>
        <h2>Sign in</h2>
        <p className="muted">Role permissions are enforced by the API, not by this screen.</p>
        {error ? <div className="error" role="alert">{error}</div> : null}
        <label className="field">
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </label>
        <label className="field">
          Password
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required minLength={8} />
        </label>
        <button className="btn" disabled={busy} type="submit">{busy ? "Signing in..." : "Sign in"}</button>
      </form>
    </div>
  );
}
