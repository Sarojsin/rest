import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../lib/auth";
import { apiFetch } from "../../lib/api";

type OnboardingStep = {
  key: string;
  label: string;
  completed: boolean;
};

type OnboardingStatus = {
  restaurant_id: string;
  stored_stage: string;
  computed_stage: string;
  stage_label: string;
  current_step_index: number;
  total_steps: number;
  percent_complete: number;
  completed_steps: string[];
  remaining_steps: string[];
  steps: OnboardingStep[];
};

const STAGE_ACTIONS: Record<string, { label: string; to: string; permission?: string }> = {
  registered: { label: "Accept invitation", to: "/staff", permission: undefined },
  owner_invited: { label: "Set up owner account", to: "/staff", permission: undefined },
  owner_activated: { label: "Owner activated", to: "/staff", permission: undefined },
  profile_complete: { label: "Complete profile", to: "/staff", permission: undefined },
  branches: { label: "Configure branches", to: "/staff/branches", permission: "branches.read" },
  tables_configured: {
    label: "Configure tables & QR",
    to: "/staff/tables",
    permission: "orders.read",
  },
  menu_configured: {
    label: "Configure menu",
    to: "/staff/menu",
    permission: "menu.manage",
  },
  staff_invited: {
    label: "Invite employees",
    to: "/staff/employees",
    permission: "employees.read",
  },
  payments_configured: {
    label: "Configure payments",
    to: "/staff/payments",
    permission: "settings.manage",
  },
  operational: { label: "Start operations", to: "/staff", permission: undefined },
};

export default function OnboardingChecklist() {
  const { me, has } = useAuth();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: OnboardingStatus = await apiFetch("/api/v1/onboarding/status");
      setStatus(data);
    } catch (err: any) {
      setError(err.detail || "Failed to load onboarding status.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <section className="section-card" aria-labelledby="onboarding-title">
        <div className="section-card-head">
          <h3 id="onboarding-title">Setup checklist</h3>
          <span className="badge muted">Loading…</span>
        </div>
        <div className="section-card-body">
          <p className="muted">Loading onboarding status…</p>
        </div>
      </section>
    );
  }

  if (!status) {
    return null;
  }

  const { percent_complete, steps, computed_stage } = status;
  const currentStep = steps.find((s) => s.key === computed_stage);
  const canCreateBranches = has("branches.read");
  const canManageMenu = has("menu.manage");
  const canManageStaff = has("employees.read");
  const canManageSettings = has("settings.manage");

  return (
    <section className="section-card" aria-labelledby="onboarding-title">
      <div className="section-card-head">
        <h3 id="onboarding-title">Setup checklist</h3>
        <span className="badge info">{percent_complete}% complete</span>
      </div>
      <div className="section-card-body">
        <div className="progress-bar" style={{ marginBottom: 16 }}>
          <div
            className="progress-fill"
            style={{ width: `${percent_complete}%` }}
          />
        </div>
        <p className="muted text-sm" style={{ marginBottom: 16 }}>
          {status.stage_label} — {steps.filter((s) => s.completed).length} of {
            steps.length
          } steps done
        </p>

        <ul className="checklist">
          {steps.map((step) => {
            const action = STAGE_ACTIONS[step.key];
            const canAccess = !action?.permission || has(action.permission);
            return (
              <li key={step.key} className="checklist-item">
                <span
                  className={`checklist-checkbox ${step.completed ? "is-done" : ""}`}
                  aria-hidden="true"
                >
                  {step.completed ? "✓" : "○"}
                </span>
                <div className="checklist-content">
                  <span
                    className={
                      step.completed ? "checklist-label is-done" : "checklist-label"
                    }
                  >
                    {step.label}
                  </span>
                </div>
                {canAccess && !step.completed && action ? (
                  <a
                    className="checklist-link"
                    href={action.to}
                    onClick={(e) => {
                      e.preventDefault();
                      window.location.href = action.to;
                    }}
                  >
                    Go →
                  </a>
                ) : null}
              </li>
            );
          })}
        </ul>

        {percent_complete === 100 && (
          <div className="checklist-complete" style={{ marginTop: 12 }}>
            <span className="badge success">Setup complete</span>
            <span className="muted text-sm">
              Your restaurant is ready for operations.
            </span>
          </div>
        )}
      </div>
    </section>
  );
}
