import { useCallback, useEffect, useRef, useState } from "react";
import { usePlatformAuth } from "../../lib/platformAuth";
import { platformFetch } from "../../lib/platformApi";

type Ticket = {
  id: string;
  restaurant_id: string;
  subject: string;
  description: string | null;
  status: string;
  priority: string;
  assigned_to_admin_id: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
};

export default function AdminSupportPage() {
  const { admin, has } = usePlatformAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createSubject, setCreateSubject] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [createPriority, setCreatePriority] = useState("medium");
  const [createRestaurantId, setCreateRestaurantId] = useState("");
  const [creating, setCreating] = useState(false);

  const loadTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let url = `/api/platform/support/tickets?page=${page}&page_size=${pageSize}`;
      if (filterStatus) url += `&status=${filterStatus}`;
      const data = await platformFetch(url);
      
      setTickets(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err.detail || "Failed to load tickets.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filterStatus]);

  useEffect(() => {
    if (admin && has("tenant.view")) {
      loadTickets();
    } else {
      setLoading(false);
    }
  }, [admin, has, loadTickets]);

  const STATUS_LABELS: Record<string, string> = {
    open: "Open",
    in_progress: "In Progress",
    resolved: "Resolved",
    closed: "Closed",
  };
  const PRIORITY_LABELS: Record<string, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };

  if (loading) {
    return (
      <div className="pf-panel" style={{ padding: 24, maxWidth: 1100 }}>
        <h1 style={{ marginTop: 0 }}>Support</h1>
        <p>Loading tickets…</p>
      </div>
    );
  }

  return (
    <div className="pf-panel" style={{ padding: 24, maxWidth: 1100 }}>
      <h1 style={{ marginTop: 0 }}>Support</h1>
      <p className="pf-muted" style={{ marginBottom: 16 }}>
        Track and manage customer support tickets.
      </p>

      {error ? <div className="pf-error">{error}</div> : null}

      <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center" }}>
        <select
          value={filterStatus || ""}
          onChange={(e) => {
            setFilterStatus(e.target.value || null);
            setPage(1);
          }}
          className="pf-input secondary"
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <button
          onClick={() => setCreateOpen(true)}
          className="pf-button"
        >
          + New Ticket
        </button>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ padding: "12px 8px" }}>Subject</th>
            <th style={{ padding: "12px 8px" }}>Restaurant</th>
            <th style={{ padding: "12px 8px" }}>Status</th>
            <th style={{ padding: "12px 8px" }}>Priority</th>
            <th style={{ padding: "12px 8px" }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket: Ticket) => (
            <tr key={ticket.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
              <td style={{ padding: "10px 8px", fontWeight: 500 }}>
                {ticket.subject}
              </td>
              <td style={{ padding: "10px 8px", fontSize: 12, color: "#64748b" }}>
                {ticket.restaurant_id}
              </td>
              <td style={{ padding: "10px 8px" }}>
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: 10,
                    fontSize: 11,
                    background: "#f1f5f9",
                    color: "#475569",
                  }}
                >
                  {STATUS_LABELS[ticket.status] || ticket.status}
                </span>
              </td>
              <td style={{ padding: "10px 8px" }}>
                {PRIORITY_LABELS[ticket.priority] || ticket.priority}
              </td>
              <td style={{ padding: "10px 8px", fontSize: 12 }}>
                {new Date(ticket.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
          {tickets.length === 0 && (
            <tr>
              <td colSpan={5} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                No tickets found.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {total > pageSize && (
        <div style={{ marginTop: 16, display: "flex", justifyContent: "center", gap: 8 }}>
          <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="pf-button secondary"
          >
            Prev
          </button>
          <span style={{ fontSize: 12, color: "#64748b" }}>
            Page {page} of {Math.ceil(total / pageSize)}
          </span>
          <button
            disabled={page * pageSize >= total}
            onClick={() => setPage(page + 1)}
            className="pf-button secondary"
          >
            Next
          </button>
        </div>
      )}

      {/* Create Ticket Dialog */}
      {createOpen && (
        <div className="pf-dialog-backdrop" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div className="pf-dialog" style={{ background: "#fff", padding: 24, borderRadius: 8, minWidth: 400 }}>
            <h2 style={{ marginTop: 0 }}>New Support Ticket</h2>
            <div style={{ marginTop: 16 }}>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
                Restaurant ID
              </label>
              <input
                className="pf-input"
                value={createRestaurantId}
                onChange={(e) => setCreateRestaurantId(e.target.value)}
                placeholder="e.g. 7f2a..."
              />
            </div>
            <div style={{ marginTop: 12 }}>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
                Subject
              </label>
              <input
                className="pf-input"
                value={createSubject}
                onChange={(e) => setCreateSubject(e.target.value)}
                placeholder="Ticket subject"
              />
            </div>
            <div style={{ marginTop: 12 }}>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
                Description
              </label>
              <textarea
                className="pf-input"
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                placeholder="Description"
                rows={3}
              />
            </div>
            <div style={{ marginTop: 12 }}>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
                Priority
              </label>
              <select
                className="pf-input"
                value={createPriority}
                onChange={(e) => setCreatePriority(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div style={{ marginTop: 20, display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => setCreateOpen(false)}
                className="pf-button secondary"
                disabled={creating}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setCreating(true);
                  try {
                    await platformFetch("/api/platform/support/tickets", {
                      method: "POST",
                      body: {
                        restaurant_id: createRestaurantId,
                        subject: createSubject,
                        description: createDescription || undefined,
                        priority: createPriority,
                      },
                    });
                    setCreateOpen(false);
                    setCreateSubject("");
                    setCreateDescription("");
                    setCreateRestaurantId("");
                    setCreatePriority("medium");
                    loadTickets();
                  } catch (err: any) {
                    setError(err.detail || "Failed to create ticket.");
                  } finally {
                    setCreating(false);
                  }
                }}
                className="pf-button"
                disabled={creating}
              >
                {creating ? "Creating…" : "Create Ticket"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}



