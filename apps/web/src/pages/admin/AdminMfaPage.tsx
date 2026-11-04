import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import type { MfaEnrollment } from "../../lib/platformApi";
import { describePlatformError, usePlatformAuth } from "../../lib/platformAuth";

/**
 * Second factor step. The login challenge lives in memory only: reloading this
 * page restarts sign-in, which is intentional (no secret in storage).
 */
export default function AdminMfaPage() {
  const { challenge, verifyMfa, startEnrollment, verifyEnrollment, clearChallenge } =
    usePlatformAuth();
  const navigate = useNavigate();

  const [code, setCode] = useState("");
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!challenge) return <Navigate to="/login" replace />;

  const enrolling = challenge.enrollment_required;

  async function beginEnrollment() {
    setError(null);
    setBusy(true);
    try {
      setEnrollment(await startEnrollment());
    } catch (err) {
      setError(describePlatformError(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (enrolling) {
        const codes = await verifyEnrollment(code.trim());
        setRecoveryCodes(codes);
      } else {
        await verifyMfa(code.trim());
        navigate("/", { replace: true });
      }
    } catch (err) {
      setError(describePlatformError(err));
    } finally {
      setBusy(false);
    }
  }

  async function copyRecoveryCodes() {
    if (!recoveryCodes) return;
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"));
      setNotice("Recovery codes copied. Store them somewhere offline, not in this browser.");
    } catch {
      setNotice("Copy failed. Select the codes and copy them manually.");
    }
  }

  function startOver() {
    clearChallenge();
    navigate("/login", { replace: true });
  }

  if (recoveryCodes) {
    return (
      <div className="pf-center">
        <div className="pf-card wide">
          <h1>Save your recovery codes</h1>
          <p className="sub">
            These codes are shown once. Each code can be used one time if your authenticator is
            unavailable. They are not stored in this browser.
          </p>

          {notice ? <div className="pf-notice">{notice}</div> : null}

          <ol className="pf-list pf-mono">
            {recoveryCodes.map((value) => (
              <li key={value}>{value}</li>
            ))}
          </ol>

          <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
            <button type="button" className="pf-button secondary" onClick={copyRecoveryCodes}>
              Copy codes
            </button>
            <button
              type="button"
              className="pf-button"
              onClick={() => navigate("/", { replace: true })}
            >
              I have saved them — continue
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="pf-center">
      <div className="pf-card">
        <h1>{enrolling ? "Set up two-factor authentication" : "Two-factor authentication"}</h1>
        <p className="sub">
          {enrolling
            ? "Platform accounts must use an authenticator app before the console opens."
            : "Enter the 6-digit code from your authenticator app."}
        </p>

        {error ? <div className="pf-error">{error}</div> : null}

        {enrolling && !enrollment ? (
          <button
            type="button"
            className="pf-button full"
            disabled={busy}
            onClick={beginEnrollment}
          >
            {busy ? "Preparing…" : "Generate authenticator secret"}
          </button>
        ) : (
          <form onSubmit={onSubmit}>
            {enrolling && enrollment ? (
              <div style={{ marginBottom: 16 }}>
                <p className="pf-muted" style={{ marginTop: 0 }}>
                  Add this secret to your authenticator app, then enter the current code.
                </p>
                <code className="pf-code">{enrollment.secret}</code>
                <p className="pf-muted pf-mono" style={{ fontSize: 12 }}>
                  {enrollment.provisioning_uri}
                </p>
              </div>
            ) : null}

            <div className="pf-field">
              <label htmlFor="platform-mfa-code">Authenticator code</label>
              <input
                id="platform-mfa-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                autoFocus
                required
                maxLength={32}
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
            </div>

            <button type="submit" className="pf-button full" disabled={busy}>
              {busy ? "Verifying…" : enrolling ? "Verify and finish" : "Verify"}
            </button>
          </form>
        )}

        <p className="pf-muted" style={{ marginBottom: 0, marginTop: 16 }}>
          <button type="button" className="pf-button secondary" onClick={startOver}>
            Start over
          </button>
        </p>
      </div>
    </div>
  );
}
