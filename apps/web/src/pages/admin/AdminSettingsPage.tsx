import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import QRCode from "qrcode";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

export default function AdminSettingsPage() {
  const { admin, has } = usePlatformAuth();
  const navigate = useNavigate();

  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [mfaActionBusy, setMfaActionBusy] = useState(false);

  // MFA enrollment inline state
  const [mfaStage, setMfaStage] = useState<"idle" | "secret" | "verify" | "codes">("idle");
  const [mfaSecret, setMfaSecret] = useState<string>("");
  const [mfaQrDataUrl, setMfaQrDataUrl] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRecoveryCodes, setMfaRecoveryCodes] = useState<string[] | null>(null);
  const [mfaError, setMfaError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSettings() {
      const url = "/api/platform/settings";
      const data = await platformFetch(url);
      setSettings(data);
      setLoading(false);
    }
    if (admin && has("settings.view")) {
      loadSettings();
    } else {
      setLoading(false);
    }
  }, [admin, has]);

  async function startMfaEnrollment() {
    setMfaError(null);
    setMfaActionBusy(true);
    try {
      const res = await platformFetch("/api/platform/mfa/enroll/start-session", {
        method: "POST",
      });
      
      setMfaSecret(res.secret);

      // Generate QR code from provisioning URI
      QRCode.toDataURL(res.provisioning_uri, { width: 260 }, (_err, url) => {
        if (url) setMfaQrDataUrl(url);
      });

      setMfaStage("secret");
    } catch (err) {
      setMfaError("Failed to start enrollment");
    } finally {
      setMfaActionBusy(false);
    }
  }

  async function verifyMfaEnrollment() {
    setMfaError(null);
    setMfaActionBusy(true);
    try {
      const res = await platformFetch("/api/platform/mfa/enroll/verify-session", {
        method: "POST",
        body: { code: mfaCode.trim() },
      });
      
      setMfaRecoveryCodes(res.recovery_codes ?? []);
      setMfaStage("codes");
    } catch (err) {
      setMfaError("Failed to verify code");
    } finally {
      setMfaActionBusy(false);
    }
  }

  async function copyRecoveryCodes() {
    if (!mfaRecoveryCodes) return;
    try {
      await navigator.clipboard.writeText(mfaRecoveryCodes.join("\n"));
    } catch {
      /* clipboard not available */
    }
  }

  if (loading || !settings) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Settings</h1>
        <p>Loading settings...</p>
      </div>
    );
  }

  const mfaEnabled = admin?.mfa_enabled ?? false;

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Settings</h1>

      {admin && has("settings.manage") ? (
        <>
          <div style={{ marginBottom: 24 }}>
            <h2 style={{ margin: "0 0 12px 0", fontSize: 16 }}>Two-Factor Authentication</h2>
            <div style={{ border: "1px solid #d9dde5", borderRadius: 8, padding: 16, background: "#f5f6f8" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>MFA Status</span>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: 4,
                    background: mfaEnabled ? "#e7f4ea" : "#fdecea",
                    color: mfaEnabled ? "#17643b" : "#b3261e",
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  {mfaEnabled ? "Enabled" : "Not enabled"}
                </span>
              </div>
              {mfaEnabled ? (
                  <button
                    type="button"
                    className="pf-button secondary"
                    disabled={mfaActionBusy}
                    onClick={startMfaEnrollment}
                  >
                    {mfaActionBusy ? "Processing…" : "Re-enroll 2FA"}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="pf-button full"
                    disabled={mfaActionBusy}
                    onClick={startMfaEnrollment}
                  >
                    {mfaActionBusy ? "Processing…" : "Enable 2FA"}
                  </button>
                )}
                <p className="pf-muted" style={{ fontSize: 12, marginTop: 8 }}>
                  {mfaEnabled
                    ? "Re-enrolling will generate a new authenticator secret and invalidate the old one."
                    : "Enable 2FA to require an authenticator app code at sign-in."}
                </p>
            </div>
          </div>

          {/* MFA Enrollment Inline Form */}
          {mfaStage === "secret" && (
            <div style={{ marginTop: 24, border: "1px solid #d9dde5", borderRadius: 8, padding: 16, background: "#ffffff" }}>
              <h2 style={{ margin: "0 0 12 0px", fontSize: 16 }}>Set up Authenticator App</h2>
              <p className="pf-muted" style={{ marginBottom: 16 }}>
                Scan the QR code with Google Authenticator, Authy, Microsoft Authenticator, or any TOTP app.
              </p>

              {mfaQrDataUrl ? (
                <div style={{ textAlign: "center", marginBottom: 16 }}>
                  <img
                    src={mfaQrDataUrl}
                    alt="Authenticator QR code"
                    style={{ width: 200, height: 200, display: "block", margin: "0 auto 12px" }}
                  />
                  <code className="pf-code" style={{ display: "block", marginBottom: 8 }}>{mfaSecret}</code>
                  <p className="pf-muted pf-mono" style={{ fontSize: 11, margin: "0"}}>
                    Secret key: {mfaSecret}
                  </p>
                </div>
              ) : (
                <div style={{ textAlign: "center", marginBottom: 16, fontSize: 11, color: "#5b6678" }}>
                  Generating QR code…
                </div>
              )}

              <p className="pf-muted" style={{ marginBottom: 12 }}>
                Enter the 6-digit code from your app to confirm setup.
              </p>

              <div className="pf-field" style={{ marginBottom: 12 }}>
                <label htmlFor="mfa-enroll-code">Authenticator code</label>
                <input
                  id="mfa-enroll-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoFocus
                  required
                  maxLength={6}
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  style={{ width: 100 }}
                />
              </div>

              {mfaError ? <div className="pf-error" style={{ marginBottom: 12 }}>{mfaError}</div> : null}

              <button
                type="button"
                className="pf-button full"
                disabled={mfaActionBusy || mfaCode.length !== 6}
                onClick={verifyMfaEnrollment}
              >
                {mfaActionBusy ? "Verifying…" : "Verify and enable"}
              </button>
              <button
                type="button"
                className="pf-button secondary"
                style={{ marginTop: 8 }}
                onClick={() => {
                  setMfaStage("idle");
                  setMfaQrDataUrl(null);
                  setMfaSecret("");
                  setMfaCode("");
                }}
              >
                Cancel
              </button>
            </div>
          )}

          {mfaStage === "codes" && (
            <div style={{ marginTop: 24, border: "1px solid #d9dde5", borderRadius: 8, padding: 16, background: "#ffffff" }}>
              <h2 style={{ margin: "0 0 12 0px", fontSize: 16 }}>Save your recovery codes</h2>
              <p className="sub">
                These codes are shown once. Each code can be used one time if your authenticator is
                unavailable. They are not stored in this browser.
              </p>
              <ol className="pf-list pf-mono" style={{ marginBottom: 16 }}>
                {(mfaRecoveryCodes ?? []).map((value) => (
                  <li key={value}>{value}</li>
                ))}
              </ol>
              <button
                type="button"
                className="pf-button secondary"
                onClick={copyRecoveryCodes}
              >
                Copy codes
              </button>
              <button
                type="button"
                className="pf-button"
                style={{ marginLeft: 8 }}
                onClick={() => {
                  setMfaStage("idle");
                  setMfaRecoveryCodes(null);
                  navigate("/", { replace: true });
                }}
              >
                Done
              </button>
            </div>
          )}

          <h2 style={{ margin: "0 0 12 0px", fontSize: 16 }}>Platform Settings</h2>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #d9dde5" }}>
                <th style={{ padding: 8, textAlign: "left" }}>Key</th>
                <th style={{ padding: 8, textAlign: "left" }}>Value</th>
                <th style={{ padding: 8, textAlign: "left" }}>Type</th>
                <th style={{ padding: 8, textAlign: "left" }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {settings.items.map((item: any) => (
                <tr key={item.key} style={{ borderBottom: "1px solid #f0f2f5" }}>
                  <td style={{ padding: "8px"}}>{item.key}</td>
                  <td style={{ padding: "8px"}}>
                    <input
                      type="text"
                      value={String(item.value)}
                      onChange={(e) => console.log("change", item.key, e.target.value)}
                      readOnly
                      disabled
                    />
                  </td>
                  <td style={{ padding: "8px"}}>{item.type}</td>
                  <td style={{ padding: "8px"}}>{item.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p className="pf-muted" style={{ color: "red" }}>
          Access denied. <a href="/admin/login">Log in</a> as a platform admin.
        </p>
      )}
    </div>
  );
}


