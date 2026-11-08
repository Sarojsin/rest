import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PlatformApiError, platformFetch } from "../../lib/platformApi";

type InvitationDetails = {
  email: string;
  purpose: string;
  tenant_name: string | null;
  expires_at: string;
};

function errorMessage(error: unknown): string {
  if (error instanceof PlatformApiError) return error.detail;
  if (error instanceof Error) return error.message;
  return "Unexpected error";
}

export default function AcceptInvitationPage() {
  const navigate = useNavigate();
  const { token } = useParams<{ token: string }>();

  const [details, setDetails] = useState<InvitationDetails | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setLoadError("This invitation link is incomplete.");
      setLoadingDetails(false);
      return;
    }
    platformFetch<InvitationDetails>(`/api/platform/auth/invitations/${token}`)
      .then((data) => {
        if (!cancelled) setDetails(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoadingDetails(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    if (password.length < 12) {
      setError("Use at least 12 characters, with upper and lower case, a number and a symbol.");
      return;
    }

    setSubmitting(true);
    try {
      await platformFetch(`/api/platform/auth/invitations/${token}/accept`, {
        method: "POST",
        body: { password, display_name: displayName.trim() },
      });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingDetails) {
    return (
      <div style={{ padding: 32, maxWidth: 440 }}>
        <h2>Complete account setup</h2>
        <p>Checking your invitation…</p>
      </div>
    );
  }

  if (done) {
    return (
      <div style={{ padding: 32, maxWidth: 440 }}>
        <h2>Account ready</h2>
        <p>
          Your password has been set{details?.tenant_name ? ` for ${details.tenant_name}` : ""}.
          Sign in with <strong>{details?.email}</strong> to continue.
        </p>
        <button className="pf-button" onClick={() => navigate("/login", { replace: true })}>
          Go to sign in
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: 32, maxWidth: 440 }}>
      <h2>Complete account setup</h2>

      {loadError ? (
        <>
          <div className="pf-error">{loadError}</div>
          <p className="pf-muted">
            Ask your platform administrator for a new invitation link. Invitation links expire and
            can be used only once.
          </p>
        </>
      ) : (
        <>
          <p className="pf-muted">
            {details?.tenant_name ? `${details.tenant_name} — ` : ""}
            setting up <strong>{details?.email}</strong>
          </p>

          {error ? <div className="pf-error">{error}</div> : null}

          <form onSubmit={handleSubmit}>
            <div className="pf-field">
              <label htmlFor="invite-display-name">Your name (optional)</label>
              <input
                id="invite-display-name"
                value={displayName}
                maxLength={120}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </div>
            <div className="pf-field">
              <label htmlFor="invite-password">New password</label>
              <input
                id="invite-password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            <div className="pf-field">
              <label htmlFor="invite-confirm">Confirm password</label>
              <input
                id="invite-confirm"
                type="password"
                autoComplete="new-password"
                required
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
              />
            </div>
            <p className="pf-muted" style={{ fontSize: 12 }}>
              At least 12 characters, including upper and lower case letters, a number and a
              symbol.
            </p>
            <div style={{ marginTop: 16, display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                type="button"
                className="pf-button secondary"
                onClick={() => navigate("/login", { replace: true })}
              >
                Cancel
              </button>
              <button type="submit" className="pf-button" disabled={submitting}>
                {submitting ? "Setting password…" : "Set password & finish"}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
