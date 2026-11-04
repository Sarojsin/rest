import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  apiFetch,
  formatMoney,
  type Branch,
  type BranchDashboardSummary,
  type BranchManager,
  type BranchSalesReport,
  type BranchTable,
  type OwnerDashboardSummary,
} from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../lib/auth";

type BranchDraft = {
  name: string;
  code: string;
  address: string;
  phone: string;
  timezone: string;
};

const EMPTY_BRANCH: BranchDraft = {
  name: "",
  code: "",
  address: "",
  phone: "",
  timezone: "UTC",
};

export default function BranchesPage() {
  const { has } = useAuth();
  const canCreate = has("branches.create");
  const canUpdate = has("branches.update");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selected, setSelected] = useState<Branch | null>(null);
  const [tables, setTables] = useState<BranchTable[]>([]);
  const [managers, setManagers] = useState<BranchManager[]>([]);
  const [reports, setReports] = useState<BranchSalesReport[]>([]);
  const [dashboard, setDashboard] = useState<BranchDashboardSummary | null>(null);
  const [ownerDashboard, setOwnerDashboard] = useState<OwnerDashboardSummary | null>(null);
  const [draft, setDraft] = useState<BranchDraft>(EMPTY_BRANCH);
  const [tableDraft, setTableDraft] = useState({ table_code: "", display_name: "", seating_capacity: "" });
  const [managerId, setManagerId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadBranches = useCallback(async () => {
    const list = await apiFetch<Branch[]>("/api/v1/branches");
    setBranches(list);
    return list;
  }, []);

  const loadOwnerDashboard = useCallback(async () => {
    try {
      setOwnerDashboard(await apiFetch<OwnerDashboardSummary>("/api/v1/branches/dashboard/owner"));
    } catch {
      setOwnerDashboard(null);
    }
  }, []);

  const loadBranchDetail = useCallback(async (branch: Branch) => {
    setSelected(branch);
    const [tableList, managerList, reportList, summary] = await Promise.all([
      apiFetch<BranchTable[]>(`/api/v1/branches/${branch.id}/tables`),
      apiFetch<BranchManager[]>(`/api/v1/branches/${branch.id}/managers`),
      apiFetch<BranchSalesReport[]>(`/api/v1/branches/${branch.id}/reports/sales`),
      apiFetch<BranchDashboardSummary>(`/api/v1/branches/${branch.id}/dashboard`),
    ]);
    setTables(tableList);
    setManagers(managerList);
    setReports(reportList);
    setDashboard(summary);
  }, []);

  useEffect(() => {
    loadBranches()
      .then((list) => {
        if (list.length > 0) return loadBranchDetail(list[0]);
        return undefined;
      })
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Could not load branches."));
    void loadOwnerDashboard();
  }, [loadBranches, loadBranchDetail, loadOwnerDashboard]);

  async function createBranch() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await apiFetch<Branch>("/api/v1/branches", {
        method: "POST",
        body: JSON.stringify({
          name: draft.name.trim(),
          code: draft.code.trim() || null,
          address: draft.address.trim() || null,
          phone: draft.phone.trim() || null,
          timezone: draft.timezone.trim() || "UTC",
        }),
      });
      setDraft(EMPTY_BRANCH);
      setNotice(`Branch “${created.name}” created.`);
      await loadBranches();
      await loadBranchDetail(created);
      await loadOwnerDashboard();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create the branch.");
    } finally {
      setBusy(false);
    }
  }

  async function createTable() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch<BranchTable>(`/api/v1/branches/${selected.id}/tables`, {
        method: "POST",
        body: JSON.stringify({
          table_code: tableDraft.table_code.trim(),
          display_name: tableDraft.display_name.trim(),
          seating_capacity: tableDraft.seating_capacity ? Number(tableDraft.seating_capacity) : null,
        }),
      });
      setTableDraft({ table_code: "", display_name: "", seating_capacity: "" });
      setNotice("Table added to the branch.");
      await loadBranchDetail(selected);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not add the table.");
    } finally {
      setBusy(false);
    }
  }

  async function assignManager() {
    if (!selected || !managerId.trim()) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch<BranchManager>(`/api/v1/branches/${selected.id}/managers`, {
        method: "POST",
        body: JSON.stringify({ membership_id: managerId.trim() }),
      });
      setManagerId("");
      setNotice("Manager assigned to the branch.");
      await loadBranchDetail(selected);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not assign the manager.");
    } finally {
      setBusy(false);
    }
  }

  async function generateReport() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch<BranchSalesReport>(
        `/api/v1/branches/${selected.id}/reports/sales/generate`,
        { method: "POST" }
      );
      setNotice("Sales report generated from recorded orders.");
      await loadBranchDetail(selected);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not generate the sales report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Multi-branch"
        title="Branches"
        sub="Each branch keeps its own tables, managers, dashboard and daily sales reports. All figures come from the server."
        actions={
          <button className="btn secondary" type="button" onClick={() => void loadOwnerDashboard()}>
            Refresh rollup
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      {ownerDashboard ? (
        <section className="report-grid" aria-label="Owner rollup">
          <article className="report-card">
            <p className="muted">Restaurant</p>
            <p className="stat">{ownerDashboard.restaurant_name}</p>
            <p className="kpi-foot">{ownerDashboard.branch_count} branches</p>
          </article>
          <article className="report-card">
            <p className="muted">Total revenue</p>
            <p className="stat">{formatMoney(ownerDashboard.total_revenue_minor, "USD")}</p>
            <p className="kpi-foot">Across branch reports</p>
          </article>
          <article className="report-card">
            <p className="muted">Orders</p>
            <p className="stat">{ownerDashboard.total_orders}</p>
            <p className="kpi-foot">Reported branch orders</p>
          </article>
          <article className="report-card">
            <p className="muted">Active branches</p>
            <p className="stat">{ownerDashboard.active_branch_count}</p>
            <p className="kpi-foot">Currently open</p>
          </article>
        </section>
      ) : null}

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="branch-list-title">
          <div className="section-card-head">
            <h3 id="branch-list-title">All branches</h3>
            <span className="muted text-sm">{branches.length} total</span>
          </div>
          <div className="section-card-body">
            {branches.length === 0 ? (
              <p className="muted">No branches yet. Add the first one below.</p>
            ) : (
              branches.map((branch) => (
                <button
                  key={branch.id}
                  type="button"
                  className={`list-row branch-row ${selected?.id === branch.id ? "is-selected" : ""}`}
                  onClick={() => void loadBranchDetail(branch)}
                >
                  <span>
                    <strong>{branch.name}</strong>
                    <span className="muted text-sm"> · {branch.code || "no code"}</span>
                  </span>
                  <span className={`badge ${branch.is_active ? "new" : "rejected"}`}>
                    {branch.is_active ? "Active" : "Inactive"}
                  </span>
                </button>
              ))
            )}

            {canCreate ? (
              <form
                className="stack"
                style={{ marginTop: "var(--space-4)" }}
                onSubmit={(event) => {
                  event.preventDefault();
                  void createBranch();
                }}
              >
              <h4 style={{ margin: 0 }}>Add a branch</h4>
              <label className="field">
                Name
                <input
                  value={draft.name}
                  maxLength={120}
                  onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                  required
                />
              </label>
              <div className="grid two">
                <label className="field">
                  Code
                  <input
                    value={draft.code}
                    maxLength={32}
                    onChange={(event) => setDraft({ ...draft, code: event.target.value })}
                  />
                </label>
                <label className="field">
                  Timezone
                  <input
                    value={draft.timezone}
                    onChange={(event) => setDraft({ ...draft, timezone: event.target.value })}
                  />
                </label>
              </div>
              <label className="field">
                Address
                <input
                  value={draft.address}
                  onChange={(event) => setDraft({ ...draft, address: event.target.value })}
                />
              </label>
              <label className="field">
                Phone
                <input
                  value={draft.phone}
                  maxLength={32}
                  onChange={(event) => setDraft({ ...draft, phone: event.target.value })}
                />
              </label>
              <button className="btn" type="submit" disabled={busy || !draft.name.trim()}>
                {busy ? "Saving…" : "Create branch"}
              </button>
              </form>
            ) : null}
          </div>
        </section>

        <div className="stack">
          {selected ? (
            <>
              <section className="section-card" aria-labelledby="branch-detail-title">
                <div className="section-card-head">
                  <h3 id="branch-detail-title">{selected.name}</h3>
                  <span className="muted text-sm">{selected.restaurant_name}</span>
                </div>
                <div className="section-card-body">
                  <div className="list-row">
                    <span className="muted">Opening hours</span>
                    <span>{selected.opening_hours || "Not set"}</span>
                  </div>
                  <div className="list-row">
                    <span className="muted">Managers</span>
                    <span>{managers.length}</span>
                  </div>
                  {dashboard ? (
                    <>
                      <div className="list-row">
                        <span className="muted">Revenue today</span>
                        <strong>{formatMoney(dashboard.total_revenue_minor, "USD")}</strong>
                      </div>
                      <div className="list-row">
                        <span className="muted">Active tables</span>
                        <span>{dashboard.active_tables}</span>
                      </div>
                      <div className="list-row">
                        <span className="muted">Low stock items</span>
                        <span>{dashboard.low_stock_count}</span>
                      </div>
                    </>
                  ) : null}
                </div>
              </section>

              <section className="section-card" aria-labelledby="branch-tables-title">
                <div className="section-card-head">
                  <h3 id="branch-tables-title">Tables</h3>
                  <span className="muted text-sm">{tables.length} configured</span>
                </div>
                <div className="section-card-body">
                  {tables.length === 0 ? <p className="muted">No tables in this branch yet.</p> : null}
                  {tables.map((table) => (
                    <div className="list-row" key={table.id}>
                      <span>
                        <strong>{table.table_code}</strong> · {table.display_name}
                      </span>
                      <span className="muted text-sm">{table.seating_capacity ?? "—"} seats</span>
                    </div>
                  ))}
                  {canUpdate ? (
                    <form
                      className="stack"
                      style={{ marginTop: "var(--space-3)" }}
                      onSubmit={(event) => {
                        event.preventDefault();
                        void createTable();
                      }}
                    >
                    <div className="grid two">
                      <label className="field">
                        Table code
                        <input
                          value={tableDraft.table_code}
                          maxLength={32}
                          onChange={(event) =>
                            setTableDraft({ ...tableDraft, table_code: event.target.value })
                          }
                          required
                        />
                      </label>
                      <label className="field">
                        Display name
                        <input
                          value={tableDraft.display_name}
                          maxLength={80}
                          onChange={(event) =>
                            setTableDraft({ ...tableDraft, display_name: event.target.value })
                          }
                          required
                        />
                      </label>
                    </div>
                    <label className="field">
                      Seats
                      <input
                        type="number"
                        min={0}
                        value={tableDraft.seating_capacity}
                        onChange={(event) =>
                          setTableDraft({ ...tableDraft, seating_capacity: event.target.value })
                        }
                      />
                    </label>
                    <button className="btn" type="submit" disabled={busy}>
                      Add table
                    </button>
                    </form>
                  ) : null}
                </div>
              </section>

              <section className="section-card" aria-labelledby="branch-managers-title">
                <div className="section-card-head">
                  <h3 id="branch-managers-title">Managers</h3>
                </div>
                <div className="section-card-body">
                  {managers.length === 0 ? <p className="muted">No branch managers assigned.</p> : null}
                  {managers.map((manager) => (
                    <div className="list-row" key={manager.id}>
                      <span>{manager.membership_id.slice(0, 8)}…</span>
                      <span className="badge info">{manager.role}</span>
                    </div>
                  ))}
                  {canUpdate ? (
                    <form
                      className="stack"
                      style={{ marginTop: "var(--space-3)" }}
                      onSubmit={(event) => {
                        event.preventDefault();
                        void assignManager();
                      }}
                    >
                    <label className="field">
                      Membership ID
                      <input
                        value={managerId}
                        onChange={(event) => setManagerId(event.target.value)}
                        placeholder="Paste a membership UUID"
                        required
                      />
                    </label>
                    <button className="btn secondary" type="submit" disabled={busy}>
                      Assign manager
                    </button>
                    </form>
                  ) : null}
                </div>
              </section>

              <section className="section-card" aria-labelledby="branch-reports-title">
                <div className="section-card-head">
                  <h3 id="branch-reports-title">Sales reports</h3>
                  {canUpdate ? (
                    <button className="btn ghost btn-sm" type="button" disabled={busy} onClick={() => void generateReport()}>
                      Generate
                    </button>
                  ) : null}
                </div>
                <div className="section-card-body">
                  {reports.length === 0 ? <p className="muted">No reports generated yet.</p> : null}
                  {reports.map((report) => (
                    <div className="audit-row" key={report.id}>
                      <div>
                        <strong>{formatMoney(report.total_sales_minor, selected.currency_code)}</strong>
                        <div className="muted text-sm">
                          {report.total_orders} orders · {report.total_orders_completed} completed
                        </div>
                      </div>
                      <time className="muted text-sm" dateTime={report.report_date}>
                        {new Date(report.report_date).toLocaleString()}
                      </time>
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : (
            <section className="section-card">
              <div className="section-card-body">
                <p className="muted">Select a branch to see its tables, managers and reports.</p>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
