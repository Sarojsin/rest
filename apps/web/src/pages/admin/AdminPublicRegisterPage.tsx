import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
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
};

export default function PublicRegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState({
    restaurant_name: "",
    restaurant_slug: "",
    owner_email: "",
    owner_name: "",
    owner_phone: "",
    plan_code: searchParams.get("plan") || "",
    trial_days: "14",
    contact_email: "",
    contact_phone: "",
    legal_name: "",
    timezone: "Asia/Kathmandu",
    currency_code: "NPR",
    source: "self_service",
    reason: "Self-service registration",
  });

  useEffect(() => {
    async function loadPlans() {
      try {
        const data = await platformFetch("/api/platform/public/plans");
        setPlans(data.items || []);
        // Auto-select plan from URL param
        const planCode = searchParams.get("plan");
        if (planCode && data.items.some((p: any) => p.code === planCode)) {
          setSelectedPlan(planCode);
          setForm({ ...form, plan_code: planCode });
        }
      } catch (err: any) {
        setError(err.message || "Failed to load plans");
      } finally {
        setLoading(false);
      }
    }
    loadPlans();
  }, [searchParams]);

  const handleChange = (field: string, value: string) => {
    setForm({ ...form, [field]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data = await platformFetch("/api/platform/public/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: {
          restaurant_name: form.restaurant_name,
          restaurant_slug: form.restaurant_slug,
          owner_email: form.owner_email,
          owner_name: form.owner_name,
          owner_phone: form.owner_phone,
          plan_code: form.plan_code,
          trial_days: parseInt(form.trial_days, 10) || 14,
          contact_email: form.contact_email,
          contact_phone: form.contact_phone,
          legal_name: form.legal_name,
          timezone: form.timezone,
          currency_code: form.currency_code,
          source: form.source,
          reason: form.reason,
        },
      });
      if (data.status === "APPROVED" && data.invitation_token) {
        // Auto-approved - show invitation page
        navigate(`/admin/register-success?token=${data.invitation_token}&restaurant=${data.restaurant_id}`);
      } else {
        // Pending approval
        navigate(`/admin/register-success?registration_id=${data.id}`);
      }
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  const selectedPlanObj = plans.find((p) => p.code === form.plan_code);

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 600 }}>
        <h1 style={{ marginTop: 0 }}>Register Restaurant</h1>
        <p>Loading plans...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 600 }}>
        <h1 style={{ marginTop: 0 }}>Register Restaurant</h1>
        <p className="pf-error">{error}</p>
        <button onClick={() => window.location.reload()} className="pf-button secondary">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 600 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Register Restaurant</h1>
          <p className="pf-muted" style={{ margin: "4px 0 0 0" }}>
            Create your restaurant account and start your free trial.
          </p>
        </div>
        <button
          onClick={() => window.location.href = "/admin/plans"}
          className="pf-button secondary"
        >
          Back to Plans
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Restaurant Name *
            </label>
            <input
              type="text"
              value={form.restaurant_name}
              onChange={(e) => handleChange("restaurant_name", e.target.value)}
              placeholder="e.g. My Restaurant"
              className="pf-input"
              required
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Slug *
            </label>
            <input
              type="text"
              value={form.restaurant_slug}
              onChange={(e) => handleChange("restaurant_slug", e.target.value)}
              placeholder="e.g. my-restaurant"
              className="pf-input"
              required
            />
            <p className="pf-muted" style={{ fontSize: 11, marginTop: 4 }}>
              URL-friendly identifier for your restaurant
            </p>
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Owner Email *
            </label>
            <input
              type="email"
              value={form.owner_email}
              onChange={(e) => handleChange("owner_email", e.target.value)}
              placeholder="owner@example.com"
              className="pf-input"
              required
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Owner Name *
            </label>
            <input
              type="text"
              value={form.owner_name}
              onChange={(e) => handleChange("owner_name", e.target.value)}
              placeholder="John Doe"
              className="pf-input"
              required
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Owner Phone
            </label>
            <input
              type="tel"
              value={form.owner_phone}
              onChange={(e) => handleChange("owner_phone", e.target.value)}
              placeholder="+1 555-000-0000"
              className="pf-input"
            />
          </div>
          <div style={{ gridColumn: "span 2" }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Select Plan *
            </label>
            <select
              value={form.plan_code}
              onChange={(e) => handleChange("plan_code", e.target.value)}
              className="pf-input"
              required
            >
              {plans.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.name} - ${(p.price_monthly_minor / 100).toFixed(2)}/month
                </option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Trial Days
            </label>
            <input
              type="number"
              value={form.trial_days}
              onChange={(e) => handleChange("trial_days", e.target.value)}
              min="0"
              max="365"
              className="pf-input"
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Contact Email
            </label>
            <input
              type="email"
              value={form.contact_email}
              onChange={(e) => handleChange("contact_email", e.target.value)}
              placeholder="contact@example.com"
              className="pf-input"
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Contact Phone
            </label>
            <input
              type="tel"
              value={form.contact_phone}
              onChange={(e) => handleChange("contact_phone", e.target.value)}
              placeholder="+1 555-000-0000"
              className="pf-input"
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Legal Name
            </label>
            <input
              type="text"
              value={form.legal_name}
              onChange={(e) => handleChange("legal_name", e.target.value)}
              placeholder="Legal Business Name"
              className="pf-input"
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Timezone
            </label>
            <input
              type="text"
              value={form.timezone}
              onChange={(e) => handleChange("timezone", e.target.value)}
              placeholder="Asia/Kathmandu"
              className="pf-input"
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Currency
            </label>
            <input
              type="text"
              value={form.currency_code}
              onChange={(e) => handleChange("currency_code", e.target.value)}
              placeholder="NPR"
              className="pf-input"
            />
          </div>
          <div style={{ gridColumn: "span 2" }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 12, fontWeight: 600 }}>
              Reason
            </label>
            <textarea
              value={form.reason}
              onChange={(e) => handleChange("reason", e.target.value)}
              placeholder="Why are you opening this restaurant?"
              className="pf-input"
              rows={3}
            />
          </div>
        </div>
        <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button
            type="button"
            className="pf-button secondary"
            onClick={() => window.location.href = "/admin/plans"}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="pf-button"
            disabled={submitting}
          >
            {submitting ? "Creating..." : "Create Restaurant"}
          </button>
        </div>
      </form>
    </div>
  );
}


