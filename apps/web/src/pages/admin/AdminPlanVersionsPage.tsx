import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { platformFetch } from "../../lib/platformApi";
import { usePlatformAuth } from "../../lib/platformAuth";

type PlanVersion = {
  id: string;
  plan_id: string;
  version: number;
  price_monthly_minor: number;
  price_annual_minor: number;
  currency_code: string;
  trial_days: number;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  features: Record<string, boolean>;
  limits: Record<string, number>;
  created_at: string;
  updated_at: string;
};

type Plan = {
  id: string;
  code: string;
  name: string;
  status: string;
  versions: PlanVersion[];
  active_version: PlanVersion | null;
};

export default function AdminPlanVersionsPage() {
  const { admin, has } = usePlatformAuth();
  const navigate = useNavigate();
  const { plan_id } = useParams<{ plan_id: string }>();

  const [plan, setPlan] = useState<Plan | null>(null);
  const [versions, setVersions] = useState<PlanVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateVersion, setShowCreateVersion] = useState(false);
  const [newVersion, setNewVersion] = useState({
    price_monthly_minor: "",
    price_annual_minor: "",
    currency_code: "NPR",
    trial_days: "",
    effective_from: "",
    reason: "",
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!plan_id) return;
    loadPlan();
  }, [plan_id]);

  async function loadPlan() {
    try {
      setLoading(true);
      const data = await platformFetch(`/api/platform/plans/${plan_id}`);
      setPlan(data);
      setVersions(data?.versions || []);
    } catch (err: any) {
      setError(err.message || "Failed to load plan");
    } finally {
      setLoading(false);
    }
  }

  async function createVersion() {
    setCreating(true);
    try {
      const data = await platformFetch(
        `/api/platform/plans/${plan_id}/versions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: {
            price_monthly_minor: parseInt(newVersion.price_monthly_minor, 10),
            price_annual_minor: parseInt(newVersion.price_annual_minor, 10),
            currency_code: newVersion.currency_code,
            trial_days: parseInt(newVersion.trial_days, 10),
            effective_from: newVersion.effective_from || undefined,
            reason: newVersion.reason,
          },
        }
      );
      setShowCreateVersion(false);
      setNewVersion({
        price_monthly_minor: "",
        price_annual_minor: "",
        currency_code: "NPR",
        trial_days: "",
        effective_from: "",
        reason: "",
      });
      await loadPlan();
    } catch (err: any) {
      setError(err.message || "Failed to create version");
    } finally {
      setCreating(false);
    }
  }

  async function publishVersion(versionId: string) {
    if (!confirm("Publish this plan version? This will make it the active version for new subscriptions.")) return;
    try {
      const data = await platformFetch(
        `/api/platform/plans/versions/${versionId}/publish`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: { reason: "Published via admin console" },
        }
      );
      await loadPlan();
    } catch (err: any) {
      setError(err.message || "Failed to publish version");
    }
  }

  async function addFeature(versionId: string, featureKey: string, enabled: boolean) {
    try {
      const data = await platformFetch(
        `/api/platform/plans/versions/${versionId}/features`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: { feature_key: featureKey, enabled, reason: "Added via admin console" },
        }
      );
      await loadPlan();
    } catch (err: any) {
      setError(err.message || "Failed to add feature");
    }
  }

  async function addLimit(versionId: string, limitKey: string, limitValue: number) {
    try {
      const data = await platformFetch(
        `/api/platform/plans/versions/${versionId}/limits`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: { limit_key: limitKey, limit_value: limitValue, reason: "Added via admin console" },
        }
      );
      await loadPlan();
    } catch (err: any) {
      setError(err.message || "Failed to add limit");
    }
  }

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Plan Versions</h1>
        <p>Loading...</p>
      </div>
    );
  }

  if (!plan || error) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 900 }}>
        <h1 style={{ marginTop: 0 }}>Plan Versions</h1>
        {error ? <p className="pf-error">{error}</p> : <p>Plan not found.</p>}
        <button onClick={() => navigate("/plans")}>Back to Plans</button>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: "0"}}>{plan.name}</h1>
          <p className="pf-muted" style={{ margin: "4px 0 0 0" }}>
            Code: {plan.code} &nbsp;|&nbsp; Status: {plan.status}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => navigate("/admin/plans")}
            className="pf-button secondary"
          >
            Back to Plans
          </button>
          {admin && has("plan.manage") && (
            <button
              onClick={() => setShowCreateVersion(true)}
              className="pf-button"
            >
              Create Version
            </button>
          )}
        </div>
      </div>

      {error && <div className="pf-error" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Versions Table */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: "0 0 12px 0", fontSize: 16 }}>Plan Versions</h2>
        {versions.length === 0 ? (
          <p className="pf-muted">No versions yet. Create the first version.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #d9dde5" }}>
                <th style={{ padding: 10, textAlign: "left" }}>Version</th>
                <th style={{ padding: 10, textAlign: "left" }}>Monthly</th>
                <th style={{ padding: 10, textAlign: "left" }}>Annual</th>
                <th style={{ padding: 10, textAlign: "left" }}>Trial Days</th>
                <th style={{ padding: 10, textAlign: "left" }}>Effective From</th>
                <th style={{ padding: 10, textAlign: "left" }}>Status</th>
                <th style={{ padding: 10, textAlign: "left" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id} style={{ borderBottom: "1px solid #f0f2f5" }}>
                  <td style={{ padding: "10px"}}>{v.version}</td>
                  <td style={{ padding: "10px"}}>
                    {(v.price_monthly_minor / 100).toLocaleString()} {v.currency_code}
                  </td>
                  <td style={{ padding: "10px"}}>
                    {(v.price_annual_minor / 100).toLocaleString()} {v.currency_code}
                  </td>
                  <td style={{ padding: "10px"}}>{v.trial_days} days</td>
                  <td style={{ padding: "10px"}}>{new Date(v.effective_from).toLocaleDateString()}</td>
                  <td style={{ padding: "10px"}}>
                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: 4,
                        background: v.is_active ? "#e7f4ea" : "#f0f2f5",
                        color: v.is_active ? "#17643b" : "#5b6678",
                        fontSize: 12,
                        fontWeight: 600,
                      }}
                    >
                      {v.is_active ? "ACTIVE" : "DRAFT"}
                    </span>
                  </td>
                  <td style={{ padding: "10px"}}>
                    {admin && has("plan.manage") && !v.is_active && (
                      <button
                        onClick={() => publishVersion(v.id)}
                        className="pf-button secondary"
                        style={{ padding: "6px 12px", fontSize: 12 }}
                      >
                        Publish
                      </button>
                    )}
                    <button
                      onClick={() => {
                        const fk = prompt("Feature key (e.g. qr_ordering):");
                        if (!fk) return;
                        const enabled = confirm("Enable this feature?");
                        addFeature(v.id, fk, enabled);
                      }}
                      className="pf-button secondary"
                      style={{ padding: "6px 12px", fontSize: 12, marginRight: 4 }}
                    >
                      Add Feature
                    </button>
                    <button
                      onClick={() => {
                        const lk = prompt("Limit key (e.g. branches):");
                        if (!lk) return;
                        const lv = parseInt(prompt("Limit value:") || "0", 10);
                        if (isNaN(lv)) return;
                        addLimit(v.id, lk, lv);
                      }}
                      className="pf-button secondary"
                      style={{ padding: "6px 12px", fontSize: 12 }}
                    >
                      Add Limit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Features & Limits for Active Version */}
      {plan.active_version && (
        <div style={{ marginBottom: 24, border: "1px solid #d9dde5", borderRadius: 8, padding: 16, background: "#f5f6f8" }}>
          <h2 style={{ margin: "0 0 12px 0", fontSize: 16 }}>Active Version Features & Limits</h2>
          <div style={{ display: "flex", gap: 32 }}>
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: "0 0 8px 0", fontSize: 14, textTransform: "uppercase", letterSpacing: "0.05em" }}>Features</h3>
              <ul style={{ listStyle: "none", padding: 0, margin: "0"}}>
                {Object.entries(plan.active_version.features).map(([key, enabled]) => (
                  <li key={key} style={{ marginBottom: 6, display: "flex", justifyContent: "space-between" }}>
                    <span>{key}</span>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: 4,
                        background: enabled ? "#e7f4ea" : "#f0f2f5",
                        color: enabled ? "#17643b" : "#5b6678",
                        fontSize: 12,
                      }}
                    >
                      {enabled ? "Enabled" : "Disabled"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: "0 0 8px 0", fontSize: 14, textTransform: "uppercase", letterSpacing: "0.05em" }}>Limits</h3>
              <ul style={{ listStyle: "none", padding: 0, margin: "0"}}>
                {Object.entries(plan.active_version.limits).map(([key, value]) => (
                  <li key={key} style={{ marginBottom: 6, display: "flex", justifyContent: "space-between" }}>
                    <span>{key}</span>
                    <span style={{ fontWeight: 600 }}>{value === -1 ? "Unlimited" : value}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Create Version Form */}
      {showCreateVersion && (
        <div style={{ marginTop: 24, border: "1px solid #d9dde5", borderRadius: 8, padding: 16, background: "#ffffff" }}>
          <h2 style={{ margin: "0 0 16px 0", fontSize: 16 }}>Create New Plan Version</h2>
          <form onSubmit={(e) => { e.preventDefault(); createVersion(); }} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>Monthly Price (minor units)</label>
                <input
                  type="number"
                  value={newVersion.price_monthly_minor}
                  onChange={(e) => setNewVersion({ ...newVersion, price_monthly_minor: e.target.value })}
                  className="pf-input"
                  required
                />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>Annual Price (minor units)</label>
                <input
                  type="number"
                  value={newVersion.price_annual_minor}
                  onChange={(e) => setNewVersion({ ...newVersion, price_annual_minor: e.target.value })}
                  className="pf-input"
                />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>Currency</label>
                <input
                  type="text"
                  value={newVersion.currency_code}
                  onChange={(e) => setNewVersion({ ...newVersion, currency_code: e.target.value.toUpperCase() })}
                  className="pf-input"
                />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>Trial Days</label>
                <input
                  type="number"
                  value={newVersion.trial_days}
                  onChange={(e) => setNewVersion({ ...newVersion, trial_days: e.target.value })}
                  className="pf-input"
                />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>Effective From (YYYY-MM-DD)</label>
                <input
                  type="date"
                  value={newVersion.effective_from}
                  onChange={(e) => setNewVersion({ ...newVersion, effective_from: e.target.value })}
                  className="pf-input"
                />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>Reason</label>
                <input
                  type="text"
                  value={newVersion.reason}
                  onChange={(e) => setNewVersion({ ...newVersion, reason: e.target.value })}
                  className="pf-input"
                  required
                />
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button
                type="submit"
                className="pf-button"
                disabled={creating}
              >
                {creating ? "Creating..." : "Create Version"}
              </button>
              <button
                type="button"
                className="pf-button secondary"
                onClick={() => setShowCreateVersion(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}


