import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import QRCode from "qrcode";
import { apiFetch, ApiError, type Table } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";

type QrImage = { tableId: string; url: string; dataUrl: string };

function buildUrl(table: Table): string {
  return `${window.location.origin}/t/${table.qr_token ?? ""}`;
}

export default function TablesPage() {
  const { has } = useAuth();
  const canManage = has("tables.manage");
  const canCreateOrder = has("orders.create");
  const [tables, setTables] = useState<Table[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [qrSheetOpen, setQrSheetOpen] = useState(false);
  const [qrImages, setQrImages] = useState<QrImage[]>([]);
  const [qrError, setQrError] = useState<string | null>(null);
  const [rotatingId, setRotatingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<Table[]>("/api/v1/tables");
      setTables(data);
      setError(null);
    } catch {
      setError("Could not load tables.");
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (!qrSheetOpen) {
      setQrImages([]);
      setQrError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const images: QrImage[] = [];
        for (const table of tables) {
          if (!table.qr_token) continue;
          const url = buildUrl(table);
          const dataUrl = await QRCode.toDataURL(url, {
            margin: 1,
            width: 320,
            errorCorrectionLevel: "M",
            color: { dark: "#111827", light: "#ffffff" },
          });
          images.push({ tableId: table.id, url, dataUrl });
        }
        if (!cancelled) setQrImages(images);
      } catch (err) {
        if (!cancelled) {
          setQrError(err instanceof ApiError ? err.detail : "Could not generate QR codes.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [qrSheetOpen, tables]);

  async function rotate(tableId: string, displayName: string) {
    const confirmed = window.confirm(
      `Regenerate the QR code for ${displayName}? Any printed codes or notes with the old link stop working immediately.`
    );
    if (!confirmed) return;
    setRotatingId(tableId);
    setError(null);
    try {
      await apiFetch(`/api/v1/tables/${tableId}/qr/rotate`, { method: "POST" });
      setQrSheetOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not regenerate the QR code.");
    } finally {
      setRotatingId(null);
    }
  }

  const summary = useMemo(() => {
    const occupied = tables.filter((table) => table.occupancy === "OCCUPIED").length;
    const checkout = tables.filter((table) => table.occupancy === "CHECKOUT").length;
    const pending = tables.reduce((total, table) => total + table.pending_qr_count, 0);
    return { occupied, checkout, pending };
  }, [tables]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Floor"
        title="Tables & QR codes"
        sub={
          <>
            {tables.length} table{tables.length === 1 ? "" : "s"} · {summary.occupied} occupied ·{" "}
            {summary.checkout} at checkout
            {summary.pending > 0 ? ` · ${summary.pending} awaiting confirmation` : ""}. Occupancy comes from
            the active dining session, not from a guest opening the QR page.
          </>
        }
        actions={
          <button
            type="button"
            className={`btn ${qrSheetOpen ? "secondary" : ""}`}
            onClick={() => setQrSheetOpen((open) => !open)}
            aria-expanded={qrSheetOpen}
          >
            {qrSheetOpen ? "Hide QR codes" : "Printable QR codes"}
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}

      {qrSheetOpen ? (
        <section className="section-card qr-sheet" aria-label="Printable table QR codes">
          <div className="section-card-head">
            <div>
              <h3>Table QR codes</h3>
              <p className="muted text-sm no-print" style={{ margin: 0 }}>
                One code per table. Print, cut, and stick each on its table — scanning opens this site and
                tags the order to that table automatically.
              </p>
            </div>
            <button type="button" className="btn no-print" onClick={() => window.print()}>
              Print these codes
            </button>
          </div>
          <div className="section-card-body">
            {qrError ? (
              <div className="error no-print" role="alert">
                {qrError}
              </div>
            ) : null}
            {qrImages.length === 0 && !qrError ? <p className="muted">Generating codes…</p> : null}
            <div className="qr-grid">
              {tables.map((table) => {
                const qr = qrImages.find((entry) => entry.tableId === table.id);
                return (
                  <article key={table.id} className="qr-card">
                    <h4>{table.display_name}</h4>
                    {qr ? (
                      <>
                        <img
                          src={qr.dataUrl}
                          alt={`QR code for ${table.display_name}`}
                          width={200}
                          height={200}
                        />
                        <p className="qr-url" aria-label={`Scanning opens ${qr.url}`}>
                          {qr.url}
                        </p>
                      </>
                    ) : (
                      <div className="qr-placeholder muted">
                        {table.qr_token ? "Generating code…" : "No active QR token"}
                      </div>
                    )}
                    <p className="qr-scanline">Scan to order from {table.display_name}</p>
                    {canManage ? (
                      <button
                        type="button"
                        className="btn ghost btn-sm no-print"
                        disabled={!table.qr_token || rotatingId === table.id}
                        onClick={() => void rotate(table.id, table.display_name)}
                      >
                        {rotatingId === table.id ? "Regenerating…" : "Regenerate"}
                      </button>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </div>
        </section>
      ) : null}

      <div className="grid tables">
        {tables.map((table) => {
          const body = (
            <>
              <div className="table-tile-top">
                <strong>{table.display_name}</strong>
                <StatusBadge status={table.occupancy} />
              </div>
              <div>
                <div className="muted text-sm">
                  {table.table_code} · {table.seating_capacity ?? "—"} seats
                </div>
                {table.pending_qr_count > 0 ? (
                  <div className="kpi-foot is-alert">
                    {table.pending_qr_count} order{table.pending_qr_count === 1 ? "" : "s"} awaiting confirmation
                  </div>
                ) : null}
                {canCreateOrder ? (
                  <span className="table-order-link">
                    Take order <span aria-hidden="true">→</span>
                  </span>
                ) : null}
              </div>
            </>
          );

          return canCreateOrder ? (
            <Link key={table.id} className={`table-tile ${table.occupancy}`} to={`/staff/tables/${table.id}/order`}>
              {body}
            </Link>
          ) : (
            <article key={table.id} className={`table-tile ${table.occupancy}`}>
              {body}
            </article>
          );
        })}
      </div>

      {tables.length === 0 ? (
        <div className="empty-state">
          <strong>No tables configured</strong>
          <span>Tables are provisioned with the restaurant.</span>
        </div>
      ) : null}
    </div>
  );
}
