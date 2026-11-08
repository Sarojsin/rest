import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { platformFetch } from "../../lib/platformApi";

export default function AcceptInvitationPage() {
  const navigate = useNavigate();
  const { token } = useParams<{ token: string }>();

  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (done) navigate("/staff", { replace: true });
  }, [done, navigate]);

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await platformFetch(`/api/platform/auth/invitations/${token}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to accept");
      const login = await platformFetch("/api/platform/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: data.admin.email, password }),
      });
      const ld = await login.json();
      if (!login.ok) throw new Error(ld.detail || "Login failed");
      setDone(true);
    } catch (e) {
      setError(e.detail || "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  if (done) return null;
  if (loading) return <div>Accepting invitation…</div>;

  return (
    <div style={{ padding: 32, maxWidth: 400 }}>
      <h2>Complete account setup</h2>
      {error && <p className="pf-error">{error}</p>}
      <p>Set up your password:</p>
      <input
        className="pf-input"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <div style={{ marginTop: 24, display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button className="pf-button secondary" onClick={() => navigate("/admin/login", { replace: true })}>
          Cancel
        </button>
        <button className="pf-button" onClick={handleSubmit} disabled={loading}>
          {loading ? "Verifying…" : "Verify and finish"}
        </button>
      </div>
    </div>
  );
}