import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  apiFetch,
  type Branch,
  type Employee,
  type Shift,
} from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../lib/auth";

const EMPTY_EMPLOYEE = {
  name: "",
  email: "",
  phone: "",
  role: "waiter",
  hire_date: new Date().toISOString().slice(0, 10),
  branch_id: "",
};

const EMPTY_SHIFT = {
  employee_id: "",
  branch_id: "",
  date: new Date().toISOString().slice(0, 10),
  start_time: "09:00",
  end_time: "17:00",
};

export default function EmployeesPage() {
  const { has } = useAuth();
  const canCreate = has("employees.create");
  const canUpdate = has("employees.update");
  const canSchedule = has("shifts.create");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [employeeDraft, setEmployeeDraft] = useState(EMPTY_EMPLOYEE);
  const [shiftDraft, setShiftDraft] = useState(EMPTY_SHIFT);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [employeeList, shiftList, branchList] = await Promise.all([
      apiFetch<Employee[]>("/api/v1/employees"),
      apiFetch<Shift[]>("/api/v1/employees/shifts"),
      apiFetch<Branch[]>("/api/v1/branches"),
    ]);
    setEmployees(employeeList);
    setShifts(shiftList);
    setBranches(branchList);
  }, []);

  useEffect(() => {
    void load().catch((err) =>
      setError(err instanceof ApiError ? err.detail : "Could not load employees.")
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
      setError(err instanceof ApiError ? err.detail : "The staff action failed.");
    } finally {
      setBusy(false);
    }
  }

  function createEmployee() {
    return run(async () => {
      await apiFetch<Employee>("/api/v1/employees", {
        method: "POST",
        body: JSON.stringify({
          name: employeeDraft.name.trim(),
          email: employeeDraft.email.trim(),
          phone: employeeDraft.phone.trim() || null,
          role: employeeDraft.role,
          hire_date: new Date(`${employeeDraft.hire_date}T00:00:00Z`).toISOString(),
          branch_id: employeeDraft.branch_id || null,
        }),
      });
      setEmployeeDraft(EMPTY_EMPLOYEE);
      return "Employee added.";
    });
  }

  function toggleEmployee(employee: Employee) {
    return run(async () => {
      await apiFetch<Employee>(`/api/v1/employees/${employee.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !employee.is_active }),
      });
      return employee.is_active ? "Employee deactivated." : "Employee reactivated.";
    });
  }

  function createShift() {
    return run(async () => {
      await apiFetch<Shift>("/api/v1/employees/shifts", {
        method: "POST",
        body: JSON.stringify({
          employee_id: shiftDraft.employee_id,
          branch_id: shiftDraft.branch_id,
          date: shiftDraft.date,
          start_time: shiftDraft.start_time,
          end_time: shiftDraft.end_time,
        }),
      });
      setShiftDraft({ ...EMPTY_SHIFT, employee_id: shiftDraft.employee_id, branch_id: shiftDraft.branch_id });
      return "Shift scheduled.";
    });
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Staff"
        title="Employees & shifts"
        sub="Employee records and daily shift rosters are separate from login memberships, so you can roster people before they get an account."
        actions={
          <button className="btn secondary" type="button" onClick={() => void load()}>
            Refresh
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="employees-title">
          <div className="section-card-head">
            <h3 id="employees-title">Employees</h3>
            <span className="muted text-sm">{employees.length} on file</span>
          </div>
          <div className="section-card-body">
            {employees.length === 0 ? <p className="muted">No employees yet.</p> : null}
            {employees.map((employee) => (
              <div className="audit-row" key={employee.id}>
                <div>
                  <strong>{employee.name}</strong>
                  <div className="muted text-sm">
                    {employee.role} · {employee.email}
                    {employee.branch_id
                      ? ` · ${branches.find((branch) => branch.id === employee.branch_id)?.name ?? "branch"}`
                      : ""}
                  </div>
                </div>
                {canUpdate ? (
                  <button
                    className="btn ghost btn-sm"
                    type="button"
                    disabled={busy}
                    onClick={() => void toggleEmployee(employee)}
                  >
                    {employee.is_active ? "Deactivate" : "Activate"}
                  </button>
                ) : null}
              </div>
            ))}

            {canCreate ? (
              <form
                className="stack"
                style={{ marginTop: "var(--space-4)" }}
                onSubmit={(event) => {
                  event.preventDefault();
                  void createEmployee();
                }}
              >
              <h4 style={{ margin: 0 }}>Add employee</h4>
              <div className="grid two">
                <label className="field">
                  Name
                  <input
                    value={employeeDraft.name}
                    onChange={(event) => setEmployeeDraft({ ...employeeDraft, name: event.target.value })}
                    required
                  />
                </label>
                <label className="field">
                  Email
                  <input
                    type="email"
                    value={employeeDraft.email}
                    onChange={(event) => setEmployeeDraft({ ...employeeDraft, email: event.target.value })}
                    required
                  />
                </label>
                <label className="field">
                  Role
                  <input
                    value={employeeDraft.role}
                    onChange={(event) => setEmployeeDraft({ ...employeeDraft, role: event.target.value })}
                  />
                </label>
                <label className="field">
                  Hire date
                  <input
                    type="date"
                    value={employeeDraft.hire_date}
                    onChange={(event) =>
                      setEmployeeDraft({ ...employeeDraft, hire_date: event.target.value })
                    }
                    required
                  />
                </label>
                <label className="field">
                  Phone
                  <input
                    value={employeeDraft.phone}
                    onChange={(event) => setEmployeeDraft({ ...employeeDraft, phone: event.target.value })}
                  />
                </label>
                <label className="field">
                  Branch
                  <select
                    value={employeeDraft.branch_id}
                    onChange={(event) =>
                      setEmployeeDraft({ ...employeeDraft, branch_id: event.target.value })
                    }
                  >
                    <option value="">Unassigned</option>
                    {branches.map((branch) => (
                      <option key={branch.id} value={branch.id}>
                        {branch.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button
                className="btn"
                type="submit"
                disabled={busy || !employeeDraft.name.trim() || !employeeDraft.email.trim()}
              >
                Add employee
              </button>
              </form>
            ) : null}
          </div>
        </section>

        <section className="section-card" aria-labelledby="shifts-title">
          <div className="section-card-head">
            <h3 id="shifts-title">Shifts</h3>
            <span className="muted text-sm">{shifts.length} scheduled</span>
          </div>
          <div className="section-card-body">
            {shifts.length === 0 ? <p className="muted">No shifts scheduled.</p> : null}
            {shifts.map((shift) => {
              const employee = employees.find((entry) => entry.id === shift.employee_id);
              return (
                <div className="list-row" key={shift.id}>
                  <span>
                    <strong>{employee?.name ?? "Employee"}</strong>
                    <span className="muted text-sm">
                      {" "}
                      · {shift.date} · {shift.start_time}–{shift.end_time}
                    </span>
                  </span>
                  <span className="badge info">{shift.status.replace("_", " ")}</span>
                </div>
              );
            })}

            {canSchedule ? (
              <form
                className="stack"
                style={{ marginTop: "var(--space-4)" }}
                onSubmit={(event) => {
                  event.preventDefault();
                  void createShift();
                }}
              >
              <h4 style={{ margin: 0 }}>Schedule a shift</h4>
              <label className="field">
                Employee
                <select
                  value={shiftDraft.employee_id}
                  onChange={(event) => {
                    const employee = employees.find((entry) => entry.id === event.target.value);
                    setShiftDraft({
                      ...shiftDraft,
                      employee_id: event.target.value,
                      branch_id: employee?.branch_id ?? shiftDraft.branch_id,
                    });
                  }}
                  required
                >
                  <option value="">Select…</option>
                  {employees.map((employee) => (
                    <option key={employee.id} value={employee.id}>
                      {employee.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Branch
                <select
                  value={shiftDraft.branch_id}
                  onChange={(event) => setShiftDraft({ ...shiftDraft, branch_id: event.target.value })}
                  required
                >
                  <option value="">Select…</option>
                  {branches.map((branch) => (
                    <option key={branch.id} value={branch.id}>
                      {branch.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="grid two">
                <label className="field">
                  Date
                  <input
                    type="date"
                    value={shiftDraft.date}
                    onChange={(event) => setShiftDraft({ ...shiftDraft, date: event.target.value })}
                    required
                  />
                </label>
                <label className="field">
                  Start
                  <input
                    type="time"
                    value={shiftDraft.start_time}
                    onChange={(event) =>
                      setShiftDraft({ ...shiftDraft, start_time: event.target.value })
                    }
                    required
                  />
                </label>
                <label className="field">
                  End
                  <input
                    type="time"
                    value={shiftDraft.end_time}
                    onChange={(event) => setShiftDraft({ ...shiftDraft, end_time: event.target.value })}
                    required
                  />
                </label>
              </div>
              <button
                className="btn secondary"
                type="submit"
                disabled={busy || !shiftDraft.employee_id || !shiftDraft.branch_id}
              >
                Schedule shift
              </button>
              </form>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}
