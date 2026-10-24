import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch, type Table } from "../../lib/api";
import { useAuth } from "../../lib/auth";

export default function TablesPage() {
  const { has } = useAuth();
  const [tables, setTables] = useState<Table[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await apiFetch<Table[]>("/api/v1/tables");
        if (!cancelled) setTables(data);
      } catch {
        if (!cancelled) setError("Could not load tables.");
      }
    }
    load();
    const timer = window.setInterval(load, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div>
      <h2>Floor</h2>
      <p className="muted">Occupancy comes from the active dining session, not from a guest opening the QR page.</p>
      {error ? <div className="error">{error}</div> : null}
      <div className="grid tables">
        {tables.map((table) => (
          <Link
            key={table.id}
            className={`card table-tile ${table.occupancy}`}
            to={has("orders.create") ? `/staff/tables/${table.id}/order` : "/staff/tables"}
          >
            <div>
              <strong>{table.display_name}</strong>
              <div className="muted">{table.table_code} · {table.seating_capacity} seats</div>
            </div>
            <div>
              <span className={`badge ${table.occupancy.toLowerCase()}`}>{table.occupancy}</span>
              {table.pending_qr_count > 0 ? (
                <div className="muted">{table.pending_qr_count} awaiting confirmation</div>
              ) : null}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
