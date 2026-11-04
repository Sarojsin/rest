import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  apiFetch,
  formatMoney,
  type Subscription,
  type SubscriptionBillingInfo,
  type SubscriptionPlan,
} from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../lib/auth";

const EMPTY_PLAN = {
  name: "",
  description: "",
  price_minor: "2900",
  billing_interval: "MONTHLY",
  trial_days: "14",
  features: "branches,inventory",
};

export default function SubscriptionPage() {
  const { has } = useAuth();
  const canCreate = has("subscriptions.create");
  const canManage = has("subscriptions.manage");
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [billing, setBilling] = useState<SubscriptionBillingInfo[]>([]);
  const [planDraft, setPlanDraft] = useState(EMPTY_PLAN);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [billingDraft, setBillingDraft] = useState({
    amount_minor: "0",
    billing_date: new Date().toISOString().slice(0, 10),
  });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [planList, current, billingList] = await Promise.all([
      apiFetch<SubscriptionPlan[]>("/api/v1/subscriptions/plans"),
      apiFetch<Subscription | null>("/api/v1/subscriptions/subscription"),
      apiFetch<SubscriptionBillingInfo[]>("/api/v1/subscriptions/billing"),
    ]);
    setPlans(planList);
    setSubscription(current);
    setBilling(billingList);
  }, []);

  useEffect(() => {
    void load().catch((err) =>
      setError(err instanceof ApiError ? err.detail : "Could not load subscriptions.")
    );
  }, [load]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The subscription action failed.");
    } finally {
      setBusy(false);
    }
  }

  function createPlan() {
    return run(async () => {
      await apiFetch<SubscriptionPlan>("/api/v1/subscriptions/plans", {
        method: "POST",
        body: JSON.stringify({
          name: planDraft.name.trim(),
          description: planDraft.description.trim() || null,
          price_minor: Number(planDraft.price_minor) || 0,
          billing_interval: planDraft.billing_interval,
          trial_days: Number(planDraft.trial_days) || 0,
          features: planDraft.features,
        }),
      });
      setPlanDraft(EMPTY_PLAN);
      return "Plan created.";
    });
  }

  function startSubscription() {
    return run(async () => {
      await apiFetch<Subscription>("/api/v1/subscriptions/subscription", {
        method: "POST",
        body: JSON.stringify({ plan_id: selectedPlan, status: "TRIAL" }),
      });
      setSelectedPlan("");
      return "Trial subscription started.";
    });
  }

  function updateSubscription(payload: { cancel_at_period_end?: boolean; status?: string }) {
    return run(async () => {
      await apiFetch<Subscription>("/api/v1/subscriptions/subscription", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      return "Subscription updated.";
    });
  }

  function addBilling() {
    if (!subscription) return Promise.resolve();
    return run(async () => {
      await apiFetch<SubscriptionBillingInfo>("/api/v1/subscriptions/billing", {
        method: "POST",
        body: JSON.stringify({
          subscription_id: subscription.id,
          amount_minor: Number(billingDraft.amount_minor) || 0,
          billing_date: new Date(`${billingDraft.billing_date}T00:00:00Z`).toISOString(),
        }),
      });
      return "Billing entry recorded.";
    });
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Billing"
        title="Subscriptions & plans"
        sub="Plans define the platform fee. A membership can have one subscription, and every billing entry is kept as a separate record."
        actions={
          <button className="btn secondary" type="button" onClick={() => void load()}>
            Refresh
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="plans-title">
          <div className="section-card-head">
            <h3 id="plans-title">Plans</h3>
            <span className="muted text-sm">{plans.length} available</span>
          </div>
          <div className="section-card-body">
            {plans.length === 0 ? <p className="muted">No plans yet.</p> : null}
            {plans.map((plan) => (
              <div className="audit-row" key={plan.id}>
                <div>
                  <strong>{plan.name}</strong>
                  <div className="muted text-sm">
                    {formatMoney(plan.price_minor, "USD")} / {plan.billing_interval.toLowerCase()} ·{" "}
                    {plan.trial_days} trial days
                  </div>
                  {plan.description ? <div className="muted text-sm">{plan.description}</div> : null}
                </div>
                {canCreate ? (
                  <button
                    className="btn ghost btn-sm"
                    type="button"
                    disabled={busy || subscription !== null}
                    onClick={() => setSelectedPlan(plan.id)}
                  >
                    Choose
                  </button>
                ) : null}
              </div>
            ))}

            {canManage ? (
              <form
                className="stack"
                style={{ marginTop: "var(--space-4)" }}
                onSubmit={(event) => {
                  event.preventDefault();
                  void createPlan();
                }}
              >
              <h4 style={{ margin: 0 }}>New plan</h4>
              <div className="grid two">
                <label className="field">
                  Name
                  <input
                    value={planDraft.name}
                    onChange={(event) => setPlanDraft({ ...planDraft, name: event.target.value })}
                    required
                  />
                </label>
                <label className="field">
                  Price (minor)
                  <input
                    type="number"
                    min={1}
                    value={planDraft.price_minor}
                    onChange={(event) =>
                      setPlanDraft({ ...planDraft, price_minor: event.target.value })
                    }
                    required
                  />
                </label>
                <label className="field">
                  Interval
                  <select
                    value={planDraft.billing_interval}
                    onChange={(event) =>
                      setPlanDraft({ ...planDraft, billing_interval: event.target.value })
                    }
                  >
                    <option value="MONTHLY">Monthly</option>
                    <option value="QUARTERLY">Quarterly</option>
                    <option value="ANNUAL">Annual</option>
                  </select>
                </label>
                <label className="field">
                  Trial days
                  <input
                    type="number"
                    min={0}
                    value={planDraft.trial_days}
                    onChange={(event) =>
                      setPlanDraft({ ...planDraft, trial_days: event.target.value })
                    }
                  />
                </label>
              </div>
              <label className="field">
                Features (comma separated)
                <input
                  value={planDraft.features}
                  onChange={(event) => setPlanDraft({ ...planDraft, features: event.target.value })}
                />
              </label>
              <label className="field">
                Description
                <textarea
                  rows={2}
                  value={planDraft.description}
                  onChange={(event) =>
                    setPlanDraft({ ...planDraft, description: event.target.value })
                  }
                />
              </label>
              <button className="btn" type="submit" disabled={busy || !planDraft.name.trim()}>
                Create plan
              </button>
              </form>
            ) : null}
          </div>
        </section>

        <div className="stack">
          <section className="section-card" aria-labelledby="current-sub-title">
            <div className="section-card-head">
              <h3 id="current-sub-title">Current subscription</h3>
            </div>
            <div className="section-card-body">
              {subscription ? (
                <>
                  <div className="list-row">
                    <span className="muted">Status</span>
                    <span className="badge info">{subscription.status}</span>
                  </div>
                  <div className="list-row">
                    <span className="muted">Plan</span>
                    <span>
                      {plans.find((plan) => plan.id === subscription.plan_id)?.name ??
                        subscription.plan_id.slice(0, 8)}
                    </span>
                  </div>
                  <div className="list-row">
                    <span className="muted">Renews</span>
                    <span>{new Date(subscription.billing_cycle_end).toLocaleDateString()}</span>
                  </div>
                  <div className="list-row">
                    <span className="muted">Cancel at period end</span>
                    <span>{subscription.cancel_at_period_end ? "Yes" : "No"}</span>
                  </div>
                  {canManage ? (
                    <div className="page-actions">
                      <button
                        className="btn secondary btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          void updateSubscription({
                            cancel_at_period_end: !subscription.cancel_at_period_end,
                          })
                        }
                      >
                        {subscription.cancel_at_period_end ? "Keep subscription" : "Cancel at period end"}
                      </button>
                      {subscription.status !== "CANCELLED" ? (
                        <button
                          className="btn ghost danger btn-sm"
                          type="button"
                          disabled={busy}
                          onClick={() => void updateSubscription({ status: "CANCELLED" })}
                        >
                          Cancel now
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </>
              ) : canCreate ? (
                <form
                  className="stack"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void startSubscription();
                  }}
                >
                  <p className="muted">No subscription yet. Pick a plan to start a trial.</p>
                  <label className="field">
                    Plan
                    <select
                      value={selectedPlan}
                      onChange={(event) => setSelectedPlan(event.target.value)}
                      required
                    >
                      <option value="">Select…</option>
                      {plans.map((plan) => (
                        <option key={plan.id} value={plan.id}>
                          {plan.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button className="btn" type="submit" disabled={busy || !selectedPlan}>
                    Start trial
                  </button>
                </form>
              ) : (
                <p className="muted">No subscription is active for this account.</p>
              )}
            </div>
          </section>

          <section className="section-card" aria-labelledby="billing-title">
            <div className="section-card-head">
              <h3 id="billing-title">Billing history</h3>
              <span className="muted text-sm">{billing.length} entries</span>
            </div>
            <div className="section-card-body">
              {billing.length === 0 ? <p className="muted">No billing entries yet.</p> : null}
              {billing.map((entry) => (
                <div className="audit-row" key={entry.id}>
                  <div>
                    <strong>{formatMoney(entry.amount_minor, entry.currency_code)}</strong>
                    <div className="muted text-sm">
                      {new Date(entry.billing_date).toLocaleDateString()} · {entry.status}
                    </div>
                  </div>
                </div>
              ))}

              {subscription && canManage ? (
                <form
                  className="stack"
                  style={{ marginTop: "var(--space-3)" }}
                  onSubmit={(event) => {
                    event.preventDefault();
                    void addBilling();
                  }}
                >
                  <div className="grid two">
                    <label className="field">
                      Amount (minor)
                      <input
                        type="number"
                        min={0}
                        value={billingDraft.amount_minor}
                        onChange={(event) =>
                          setBillingDraft({ ...billingDraft, amount_minor: event.target.value })
                        }
                      />
                    </label>
                    <label className="field">
                      Billing date
                      <input
                        type="date"
                        value={billingDraft.billing_date}
                        onChange={(event) =>
                          setBillingDraft({ ...billingDraft, billing_date: event.target.value })
                        }
                      />
                    </label>
                  </div>
                  <button className="btn secondary" type="submit" disabled={busy}>
                    Record billing entry
                  </button>
                </form>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
