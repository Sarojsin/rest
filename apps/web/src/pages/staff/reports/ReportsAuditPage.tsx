import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, ApiError, type AuditEvent } from "../../../lib/api";
import { useAuth } from "../../../lib/auth";

const PAGE_SIZE = 50;

export default function ReportsAuditPage() {
  const { has } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    if (!has("audit.read")) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<AuditEvent[]>("/api/v1/audit-events");
      setEvents(data);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 403 || err.status === 401)) {
        // No audit permission — treat as empty rather than an outage.
        setEvents([]);
      } else {
        setError(err instanceof ApiError ? err.detail : "Could not load audit trail.");
      }
    } finally {
      setLoading(false);
    }
  }, [has]);

  useEffect(() => {
    void load();
  }, [load]);

  const actions = useMemo(
    () => Array.from(new Set(events.map((event) => event.action))).sort(),
    [events]
  );

  const filtered = useMemo(() => {
    const text = search.toLowerCase();
    return events.filter((event) => {
      const matchesAction = !actionFilter || event.action === actionFilter;
      const matchesText =
        !text ||
        (event.detail ?? "").toLowerCase().includes(text) ||
        event.entity_type.toLowerCase().includes(text) ||
        event.action.toLowerCase().includes(text);
      return matchesAction && matchesText;
    });
  }, [events, actionFilter, search]);

  if (!has("audit.read")) {
    return (
      <div className="empty-state">
        <strong>Audit trail is restricted</strong>
        <span>Your role cannot read the audit trail. Ask an owner or manager for access.</span>
      </div>
    );
  }

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {loading ? <p className="muted">Loading audit trail…</p> : null}

      <div className="toolbar">
        <div className="toolbar-group">
          <select
            className="field"
            value={actionFilter}
            onChange={(event) => setActionFilter(event.target.value)}
            aria-label="Filter by action"
          >
            <option value="">All actions</option>
            {actions.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
          <input
            className="field"
            placeholder="Search detail or entity…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <span className="muted text-sm">
          {filtered.length} of {events.length} events
        </span>
      </div>

      <section className="section-card">
        <div className="section-card-head">
          <h3>Audit trail</h3>
          <span className="muted text-sm">Append-only</span>
        </div>
        <div className="section-card-body">
          {filtered.length === 0 ? (
            <p className="muted">
              {events.length === 0 ? "No audit events recorded yet." : "No events match the filter."}
            </p>
          ) : (
            filtered.slice(0, PAGE_SIZE).map((event) => (
              <div className="audit-row" key={event.id}>
                <div>
                  <span className="audit-action">{event.action}</span>
                  <div>{event.detail || event.entity_type}</div>
                  <span className="muted text-sm">
                    {event.entity_type.slice(0, 8)}…{event.entity_id.slice(0, 8)}
                  </span>
                </div>
                <time className="muted text-sm" dateTime={event.occurred_at}>
                  {new Date(event.occurred_at).toLocaleString()}
                </time>
              </div>
            ))
          )}
          {filtered.length > PAGE_SIZE ? (
            <p className="muted text-sm" style={{ marginTop: "var(--space-3)" }}>
              Showing first {PAGE_SIZE}. Refine the filter to narrow down.
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
