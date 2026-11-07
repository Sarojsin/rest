import React, { useEffect, useState } from "react";
import { platformFetch } from "../../lib/platformApi";

type Plan = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  price_monthly_minor: number;
  price_annual_minor: number;
  currency_code: string;
  trial_days: number;
  version: number;
  version_price_monthly: number | null;
  version_price_annual: number | null;
  version_trial_days: number | null;
  version_active: boolean;
};

export default function PublicPlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPlans() {
      try {
        const data = await platformFetch<{ items: Plan[] }>("/api/platform/public/plans");
        setPlans(data.items || []);
      } catch (err: any) {
        setError(err.message || "Failed to load plans");
      } finally {
        setLoading(false);
      }
    }
    loadPlans();
  }, []);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Platform Plans</h1>
        <p>Loading plans...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0 }}>Platform Plans</h1>
        <p className="pf-error">{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1400 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Platform Plans</h1>
          <p className="pf-muted" style={{ margin: "4px 0 0 0" }}>
            Choose a plan to start your restaurant subscription.
          </p>
        </div>
        <div>
          <a href="/admin/register" className="pf-button">
              Register Restaurant
            </a>
        </div>
      </div>

      {error && <div className="pf-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
        {plans.map((plan) => (
          <div
            key={plan.id}
            style={{
              border: "1px solid #d9dde5",
              borderRadius: 8,
              padding: 16,
              background: "#ffffff",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 8 }}>
              <div>
                <h2 style={{ margin: 0 }}>{plan.name}</h2>
                <p className="pf-muted" style={{ margin: "4px 0 0 0" }}>
                  {plan.code} &nbsp;|&nbsp; v{plan.version}
                </p>
              </div>
              {plan.version_active ? (
                <span
                  style={{
                    padding: "4px 8px",
                    borderRadius: 4,
                    background: "#e7f4ea",
                    color: "#17643b",
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  Active
                </span>
              ) : null}
            </div>
            <p style={{ margin: "8px 0", color: "#5b6678" }}>{plan.description || "No description"}</p>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: "#5b6678", marginBottom: 4 }}>Monthly</div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>
                {(plan.version_price_monthly ?? plan.price_monthly_minor) / 100} {plan.currency_code}
              </span>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: "#5b6678", marginBottom: 4 }}>Annual</div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>
                {(plan.version_price_annual ?? plan.price_annual_minor) / 100} {plan.currency_code}
              </span>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: "#5b6678", marginBottom: 4 }}>Trial</div>
              <span style={{ fontWeight: 600 }}>{plan.version_trial_days ?? plan.trial_days} days</span>
            </div>
            <div style={{ marginTop: 16 }}>
              <a
                href={`/admin/register?plan=${plan.code}`}
                className="pf-button"
                style={{ display: "block", width: "100%", textAlign: "center" }}
              >
                Select Plan
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

