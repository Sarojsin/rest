import React, { useEffect, useState } from "react";
import { platformFetch } from "../../lib/platformApi";
import { usePlatformAuth } from "../../lib/platformAuth";

export default function AdminTrialLifecyclePage() {
  const { admin, has } = usePlatformAuth();
  const [trialStatus, setTrialStatus] = useState<{
    subscription_id: string;
    restaurant_id: string;
    status: string;
    trial_ends_at: string | null;
    days_remaining: number;
    is_expiring_soon: boolean;
    trial_extension_count: number;
    trial_extension_total_days: number;
    can_extend: boolean;
  } | null>(null);
  const [expiringTrials, setExpiringTrials] = useState<{
    subscription_id: string;
    restaurant_id: string;
    trial_ends_at: string;
    days_remaining: number;
  }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [extending, setExtending] = useState<string | null>(null);
  const [expiring, setExpiring] = useState<string | null>(null);
  const [newDays, setNewDays] = useState("");

  useEffect(() => {
    loadTrialStatus();
    loadExpiringTrials();
  }, []);

  async function loadTrialStatus() {
    try {
      setLoading(true);
      const tenantsRes = await platformFetch("/api/platform/tenants");
      if (!tenantsRes.ok) throw new Error("Failed to load tenants");
      const tenantsData = (await tenantsRes.json()) as { items: Array<{ id: string }> };
      const tenants = tenantsData.items || [];

      for (const t of tenants) {
        const entRes = await platformFetch(`/api/platform/tenants/${t.id}/entitlements`);
        if (entRes.ok) {
          const entData = await entRes.json();
          if (entData.subscription_id) {
            const subRes = await platformFetch(
              `/api/platform/subscriptions/${entData.subscription_id}/trial-status`
            );
            if (subRes.ok) {
              const subData = await subRes.json();
              setTrialStatus(subData as {
                subscription_id: string;
                restaurant_id: string;
                status: string;
                trial_ends_at: string | null;
                days_remaining: number;
                is_expiring_soon: boolean;
                trial_extension_count: number;
                trial_extension_total_days: number;
                can_extend: boolean;
              });
              break;
            }
          }
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load trial status");
    } finally {
      setLoading(false);
    }
  }

  async function loadExpiringTrials() {
    try {
      const res = await platformFetch("/api/platform/trials/expiring?days_ahead=7");
      setExpiringTrials(res.trials || []);
    } catch {
      // Silently fail - not critical
    }
  }

  async function extendTrial(subId: string, days: number) {
    setExtending(subId);
    try {
      const data = await platformFetch(
        `/api/platform/subscriptions/${subId}/extend-trial`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: { days, reason: "Trial extension via admin console" },
        }
      );
      await loadTrialStatus();
      setNewDays("");
    } catch (err: any) {
      setError(err.message || "Failed to extend trial");
    } finally {
      setExtending(null);
    }
  }

  async function expireTrial(subId: string) {
    if (
      !confirm(
        "Expire this trial? The tenant will lose access to platform features until they subscribe."
      )
    )
      return;
    setExpiring(subId);
    try {
      const data = await platformFetch(
        `/api/platform/subscriptions/${subId}/expire-trial`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: { reason: "Manual expiration via admin console" },
        }
      );
      await loadTrialStatus();
      await loadExpiringTrials();
    } catch (err: any) {
      setError(err.message || "Failed to expire trial");
    } finally {
      setExpiring(null);
    }
  }

  async function expireAllExpired() {
    if (
      !confirm(
        "Expire all trials past their end date? This cannot be undone."
      )
    )
      return;
    try {
      const res = await platformFetch("/api/platform/trials/expire-expired", {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to expire trials");
      await loadTrialStatus();
      await loadExpiringTrials();
    } catch (err: any) {
      setError(err.message || "Failed to expire trials");
    }
  }

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Trial Lifecycle</h1>
        <p>Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Trial Lifecycle</h1>
        <p className="pf-error">{error}</p>
        <button onClick={() => window.location.href = "/admin/subscriptions"}>Back to Subscriptions</button>
      </div>
    );
  }

  const trial = trialStatus;

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Trial Lifecycle</h1>
          <p className="pf-muted" style={{ margin: "4px 0 0 0" }}>
            Manage trial subscriptions, extensions, and expirations.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => window.location.href = "/admin/subscriptions"}
            className="pf-button secondary"
          >
            Back to Subscriptions
          </button>
          <button
            onClick={expireAllExpired}
            disabled={expiring}
            className="pf-button secondary"
          >
            {expiring ? "Expiring..." : "Expire All Past Due"}
          </button>
        </div>
      </div>

      {error && <div className="pf-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div style={{ marginBottom: 24, border: "1px solid #d9dde5", borderRadius: 8, padding: 16, background: "#f5f6f8" }}>
        <h2 style={{ margin: "0 0 12px 0", fontSize: 16 }}>Trial Status</h2>
        {!trial ? (
          <p>No active trial subscription found.</p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            <div>
              <h3 style={{ margin: "0 0 4px 0", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "#5b6678" }}>Status</h3>
              <span
                style={{
                  padding: "4px 10px",
                  borderRadius: 4,
                  background: trial.status === "TRIALING" ? "#e7f4ea" : "#f0f2f5",
                  color: trial.status === "TRIALING" ? "#17643b" : "#5b6678",
                  fontSize: 13,
                  fontWeight: 600,
                }}
              >
                {trial.status}
              </span>
            </div>
            <div>
              <h3 style={{ margin: "0 0 4px 0", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "#5b6678" }}>Days Remaining</h3>
              <span style={{ fontSize: 24, fontWeight: 700 }}>{trial.days_remaining}</span>
            </div>
            <div>
              <h3 style={{ margin: "0 0 4px 0", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "#5b6678" }}>Ends At</h3>
              <span style={{ fontSize: 13 }}>{trial.trial_ends_at ? new Date(trial.trial_ends_at).toLocaleDateString() : "N/A"}</span>
            </div>
            <div>
              <h3 style={{ margin: "0 0 4px 0", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "#5b6678" }}>Extensions Used</h3>
              <span style={{ fontSize: 13 }}>{trial.trial_extension_count}</span>
            </div>
            <div>
              <h3 style={{ margin: "0 0 4px 0", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "#5b6678" }}>Total Extension Days</h3>
              <span style={{ fontSize: 13 }}>{trial.trial_extension_total_days}</span>
            </div>
          </div>
        )}
      </div>

      {trial && trial.status === "TRIALING" && (
        <div style={{ marginBottom: 24, border: "1px solid #d9dde5", borderRadius: 8, padding: 16, background: "#ffffff" }}>
          <h2 style={{ margin: "0 0 12px 0", fontSize: 16 }}>Extend Trial</h2>
          <p className="pf-muted" style={{ marginBottom: 12 }}>
            Extend the trial by additional days. Extensions count toward the total limit ({trial.trial_extension_total_days} days used so far).
          </p>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 600 }}>Days to Extend</label>
              <input
                type="number"
                value={newDays}
                onChange={(e) => setNewDays(e.target.value)}
                placeholder="Days"
                className="pf-input"
                style={{ width: 100 }}
              />
            </div>
            <button
              onClick={() => {
                const days = parseInt(newDays, 10);
                if (!days || days < 1) {
                  setError("Please enter a valid number of days");
                  return;
                }
                extendTrial(trial.subscription_id, days);
              }}
              disabled={extending === trial.subscription_id || !newDays || parseInt(newDays, 10) < 1}
              className="pf-button"
            >
              {extending === trial.subscription_id ? "Extending..." : "Extend Trial"}
            </button>
          </div>
          <p className="pf-muted" style={{ marginTop: 8, fontSize: 12 }}>
            Can extend: {trial.can_extend ? "Yes" : "No (limit reached - superadmin required)"}
          </p>
        </div>
      )}

      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: "0 0 12px 0", fontSize: 16 }}>Expiring Trials (Next 7 Days)</h2>
        {expiringTrials.length === 0 ? (
          <p className="pf-muted">No trials expiring soon.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #d9dde5" }}>
                <th style={{ padding: 10, textAlign: "left" }}>Tenant ID</th>
                <th style={{ padding: 10, textAlign: "left" }}>Subscription ID</th>
                <th style={{ padding: 10, textAlign: "left" }}>Expires</th>
                <th style={{ padding: 10, textAlign: "left" }}>Days Remaining</th>
                <th style={{ padding: 10, textAlign: "left" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {expiringTrials.map((t) => (
                <tr key={t.subscription_id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                  <td style={{ padding: 10 }}>{t.restaurant_id}</td>
                  <td style={{ padding: 10 }}>{t.subscription_id}</td>
                  <td style={{ padding: 10 }}>{new Date(t.trial_ends_at).toLocaleDateString()}</td>
                  <td style={{ padding: 10 }}>
                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: 4,
                        background: t.days_remaining <= 1 ? "#fdecea" : "#fff4e5",
                        color: t.days_remaining <= 1 ? "#b3261e" : "#9a6200",
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      {t.days_remaining} days
                    </span>
                  </td>
                  <td style={{ padding: 10 }}>
                    <button
                      onClick={() => expireTrial(t.subscription_id)}
                      disabled={expiring === t.subscription_id}
                      className="pf-button secondary"
                      style={{ padding: "6px 12px", fontSize: 11 }}
                    >
                      {expiring === t.subscription_id ? "Expiring..." : "Expire Now"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ marginTop: 24, borderTop: "1px solid #d9dde5", paddingTop: 16 }}>
        <h3 style={{ margin: "0 0 8px 0", fontSize: 14 }}>Trial Lifecycle Rules</h3>
        <ul style={{ margin: 0, paddingLeft: 20, color: "#5b6678", fontSize: 13 }}>
          <li>Trials automatically expire when <code>trial_ends_at</code> passes</li>
          <li>Extensions are limited per-action (default 30 days) and total (default 60 days)</li>
          <li>Only a superadmin can override extension limits</li>
          <li>Expired trials cannot be re-extended</li>
          <li>Use "Expire All Past Due" to bulk-expire trials past their end date</li>
        </ul>
      </div>
    </div>
  );
}


