import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { platformFetch } from "../../lib/platformApi";

export default function AcceptInvitationPage() {
  const navigate = useNavigate();
  const params = useSearchParams();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
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
        body: JSON.stringify({ password, mfa_code: mfaCode }),
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
      <p>Set up your password and authenticator code:</p>
      <input
        className="pf-input"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <input
        className="pf-input"
        type="text"
        value={mfaCode}
        onChange={(e) => setMfaCode(e.target.value)}
        placeholder="Authenticator code"
        maxLength={6}
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