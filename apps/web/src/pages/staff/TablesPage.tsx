import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import QRCode from "qrcode";
import { apiFetch, ApiError, type Table } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { Sheet } from "../../components/Sheet";

type QrImage = { tableId: string; url: string; dataUrl: string };

type EditorState =
  | { mode: "create"; table: null }
  | { mode: "edit"; table: Table };

type Draft = {
  table_code: string;
  display_name: string;
  seating_capacity: string;
  sort_order: string;
};

const EMPTY_DRAFT: Draft = {
  table_code: "",
  display_name: "",
  seating_capacity: "",
  sort_order: "",
};

function buildUrl(table: Table): string {
  return `${window.location.origin}/t/${table.qr_token ?? ""}`;
}

/** Next free numeric code after seeded codes like T1..T6 (owner can override). */
function suggestNextCode(tables: Table[]): string {
  let max = 0;
  for (const table of tables) {
    const match = /^T(\d+)$/i.exec(table.table_code);
    if (match) max = Math.max(max, Number.parseInt(match[1], 10));
  }
  return `T${max + 1}`;
}

export default function TablesPage() {
  const { has } = useAuth();
  const canConfigure = has("tables.configure");
  const canCreateOrder = has("orders.create");
  const [tables, setTables] = useState<Table[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [qrSheetOpen, setQrSheetOpen] = useState(false);
  const [qrImages, setQrImages] = useState<QrImage[]>([]);
  const [qrError, setQrError] = useState<string | null>(null);
  const [rotatingId, setRotatingId] = useState<string | null>(null);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      // Cached archive data saves owners a second request; the floor grid is
      // still filtered below, so waiter/cashier surfaces are unchanged.
      const data = await apiFetch<Table[]>(
        canConfigure ? "/api/v1/tables?include_archived=true" : "/api/v1/tables"
      );
      setTables(data);
      setError(null);
    } catch {
      setError("Could not load tables.");
    }
  }, [canConfigure]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  const floorTables = useMemo(
    () => tables.filter((table) => table.status !== "ARCHIVED"),
    [tables]
  );
  const archivedTables = useMemo(
    () => tables.filter((table) => table.status === "ARCHIVED"),
    [tables]
  );

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
        for (const table of floorTables) {
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
  }, [qrSheetOpen, floorTables]);

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

  function openCreate() {
    setDraft({
      table_code: suggestNextCode(floorTables),
      display_name: "",
      seating_capacity: "",
      sort_order: "",
    });
    setFormError(null);
    setEditor({ mode: "create", table: null });
  }

  function openEdit(table: Table) {
    setDraft({
      table_code: table.table_code,
      display_name: table.display_name,
      seating_capacity: table.seating_capacity == null ? "" : String(table.seating_capacity),
      sort_order: String(table.sort_order),
    });
    setFormError(null);
    setEditor({ mode: "edit", table });
  }

  function closeEditor() {
    setEditor(null);
    setDraft(EMPTY_DRAFT);
    setFormError(null);
  }

  async function saveTable() {
    if (!editor) return;
    const code = draft.table_code.trim().toUpperCase();
    const name = draft.display_name.trim();
    const seats = draft.seating_capacity.trim();
    const sortInput = draft.sort_order.trim();
    if (editor.mode === "create" && !/^[A-Z0-9-]{1,32}$/.test(code)) {
      setFormError("Code: 1–32 letters, numbers, or dashes (e.g. T7 or PATIO-1).");
      return;
    }
    if (name.length === 0 || name.length > 80) {
      setFormError("Give the table a name of up to 80 characters.");
      return;
    }
    if (seats && !/^\d+$/.test(seats)) {
      setFormError("Seats must be a whole number.");
      return;
    }
    if (sortInput && !/^\d+$/.test(sortInput)) {
      setFormError("Sort order must be a whole number.");
      return;
    }

    setSaving(true);
    setFormError(null);
    setError(null);
    try {
      if (editor.mode === "create") {
        const created = await apiFetch<Table>("/api/v1/tables", {
          method: "POST",
          body: JSON.stringify({
            table_code: code,
            display_name: name,
            ...(seats ? { seating_capacity: Number(seats) } : {}),
            ...(sortInput ? { sort_order: Number(sortInput) } : {}),
          }),
        });
        setNotice(
          `Created ${created.display_name} (${created.table_code}) with a fresh QR code — open “Printable QR codes” to print it.`
        );
      } else {
        await apiFetch<Table>(`/api/v1/tables/${editor.table.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            display_name: name,
            ...(seats ? { seating_capacity: Number(seats) } : { seating_capacity: null }),
            ...(sortInput ? { sort_order: Number(sortInput) } : {}),
          }),
        });
        setNotice("Table updated.");
      }
      closeEditor();
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.detail : "Could not save the table.");
    } finally {
      setSaving(false);
    }
  }

  async function setStatus(table: Table, status: "ACTIVE" | "OUT_OF_SERVICE") {
    const confirmed = window.confirm(
      status === "OUT_OF_SERVICE"
        ? `Take ${table.display_name} out of service? Guests can no longer scan its QR code to order.`
        : `Put ${table.display_name} back in service?`
    );
    if (!confirmed) return;
    setSaving(true);
    setFormError(null);
    try {
      await apiFetch(`/api/v1/tables/${table.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setNotice(
        status === "OUT_OF_SERVICE" ? "Table out of service." : "Table back in service."
      );
      closeEditor();
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.detail : "Could not update the table.");
    } finally {
      setSaving(false);
    }
  }

  async function archive(table: Table) {
    const confirmed = window.confirm(
      `Archive ${table.display_name}? Its printed QR code stops working immediately. The table can be restored later.`
    );
    if (!confirmed) return;
    setSaving(true);
    setFormError(null);
    try {
      await apiFetch(`/api/v1/tables/${table.id}/archive`, { method: "POST" });
      setNotice("Table archived and hidden from the floor.");
      closeEditor();
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.detail : "Could not archive the table.");
    } finally {
      setSaving(false);
    }
  }

  async function restore(table: Table) {
    setSaving(true);
    setError(null);
    try {
      const restored = await apiFetch<Table>(`/api/v1/tables/${table.id}/restore`, {
        method: "POST",
      });
      setNotice(
        `${restored.display_name} is back in service with a new QR code — reprint it via “Printable QR codes”.`
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not restore the table.");
    } finally {
      setSaving(false);
    }
  }

  const summary = useMemo(() => {
    const occupied = floorTables.filter((table) => table.occupancy === "OCCUPIED").length;
    const checkout = floorTables.filter((table) => table.occupancy === "CHECKOUT").length;
    const pending = floorTables.reduce((total, table) => total + table.pending_qr_count, 0);
    return { occupied, checkout, pending };
  }, [floorTables]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Floor"
        title="Tables & QR codes"
        sub={
          <>
            {floorTables.length} table{floorTables.length === 1 ? "" : "s"} · {summary.occupied}{" "}
            occupied · {summary.checkout} at checkout
            {summary.pending > 0 ? ` · ${summary.pending} awaiting confirmation` : ""}. Occupancy
            comes from the active dining session, not from a guest opening the QR page.
          </>
        }
        actions={
          <>
            {canConfigure ? (
              <button type="button" className="btn" onClick={openCreate}>
                Add table
              </button>
            ) : null}
            <button
              type="button"
              className={`btn ${qrSheetOpen ? "secondary" : ""}`}
              onClick={() => setQrSheetOpen((open) => !open)}
              aria-expanded={qrSheetOpen}
            >
              {qrSheetOpen ? "Hide QR codes" : "Printable QR codes"}
            </button>
          </>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <Sheet
        open={editor !== null}
        onClose={closeEditor}
        title={editor?.mode === "edit" ? `Edit ${editor.table.display_name}` : "Add a table"}
      >
        <div className="form-row">
          <label htmlFor="table-code">Table code</label>
          <input
            id="table-code"
            value={draft.table_code}
            maxLength={32}
            disabled={editor?.mode === "edit"}
            onChange={(e) => setDraft({ ...draft, table_code: e.target.value })}
            placeholder="e.g. T7 or PATIO-1"
            tabIndex={editor?.mode === "edit" ? -1 : undefined}
          />
          {editor?.mode === "edit" ? (
            <p className="text-sm muted" style={{ margin: 0 }}>
              Codes are permanent — they identify the table across sessions and printed QR codes.
            </p>
          ) : null}
        </div>
        <div className="form-row">
          <label htmlFor="table-name">Display name</label>
          <input
            id="table-name"
            value={draft.display_name}
            maxLength={80}
            onChange={(e) => setDraft({ ...draft, display_name: e.target.value })}
            placeholder="e.g. Table 7, Patio 1, Window corner"
          />
        </div>
        <div className="form-row">
          <label htmlFor="table-seats">Seats (optional)</label>
          <input
            id="table-seats"
            type="number"
            min={1}
            max={40}
            value={draft.seating_capacity}
            onChange={(e) => setDraft({ ...draft, seating_capacity: e.target.value })}
          />
        </div>
        <div className="form-row">
          <label htmlFor="table-sort">Sort order (optional)</label>
          <input
            id="table-sort"
            type="number"
            min={0}
            max={1000}
            value={draft.sort_order}
            onChange={(e) => setDraft({ ...draft, sort_order: e.target.value })}
          />
        </div>
        {formError ? (
          <div className="error" role="alert">
            {formError}
          </div>
        ) : null}
        <div className="table-editor-actions">
          <button type="button" className="btn ok" disabled={saving} onClick={saveTable}>
            {saving ? "Saving…" : editor?.mode === "edit" ? "Save changes" : "Create table"}
          </button>
          {editor?.mode === "edit" ? (
            <>
              {editor.table.status === "OUT_OF_SERVICE" ? (
                <button
                  type="button"
                  className="btn secondary"
                  disabled={saving}
                  onClick={() => setStatus(editor.table, "ACTIVE")}
                >
                  Back in service
                </button>
              ) : (
                <button
                  type="button"
                  className="btn secondary"
                  disabled={saving}
                  onClick={() => setStatus(editor.table, "OUT_OF_SERVICE")}
                >
                  Out of service
                </button>
              )}
              <button
                type="button"
                className="btn danger"
                disabled={saving}
                onClick={() => archive(editor.table)}
              >
                Archive
              </button>
            </>
          ) : null}
        </div>
      </Sheet>

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
              {floorTables.map((table) => {
                const qr = qrImages.find((entry) => entry.tableId === table.id);
                return (
                  <article key={table.id} className="qr-card">
                    <h4>
                      {table.display_name}
                      {table.status === "OUT_OF_SERVICE" ? " (out of service)" : ""}
                    </h4>
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
                    {canConfigure ? (
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
        {floorTables.map((table) => {
          const body = (
            <>
              <div className="table-tile-top">
                <strong>{table.display_name}</strong>
                <StatusBadge status={table.occupancy} />
              </div>
              <div>
                <div className="muted text-sm">
                  {table.table_code} · {table.seating_capacity ?? "—"} seats
                  {table.status === "OUT_OF_SERVICE" ? " · " : ""}
                  {table.status === "OUT_OF_SERVICE" ? (
                    <StatusBadge status="OUT_OF_SERVICE" />
                  ) : null}
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

          return canConfigure ? (
            <article key={table.id} className={`table-tile ${table.occupancy}`}>
              {canCreateOrder ? (
                <Link className="table-tile-body" to={`/staff/tables/${table.id}/order`}>
                  {body}
                </Link>
              ) : (
                <div className="table-tile-body">{body}</div>
              )}
              <div className="table-tile-actions">
                <button type="button" className="btn ghost btn-sm" onClick={() => openEdit(table)}>
                  Edit
                </button>
              </div>
            </article>
          ) : canCreateOrder ? (
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

      {floorTables.length === 0 ? (
        <div className="empty-state">
          <strong>No tables configured</strong>
          {canConfigure ? (
            <span>Add your first table to start taking orders.</span>
          ) : (
            <span>Tables are added by the owner or a manager.</span>
          )}
          {canConfigure ? (
            <div>
              <button type="button" className="btn" onClick={openCreate}>
                Add table
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {canConfigure && archivedTables.length > 0 ? (
        <details className="archived-tables">
          <summary>
            Archived tables ({archivedTables.length})
          </summary>
          <div className="grid tables">
            {archivedTables.map((table) => (
              <article key={table.id} className="table-tile archived">
                <div>
                  <strong>{table.display_name}</strong>
                  <div className="muted text-sm">{table.table_code} · no active QR</div>
                </div>
                <button
                  type="button"
                  className="btn secondary btn-sm"
                  disabled={saving}
                  onClick={() => restore(table)}
                >
                  Restore
                </button>
              </article>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
