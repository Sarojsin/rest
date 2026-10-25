import { useCallback, useEffect, useState } from "react";
import { ApiError, apiFetch, type PaymentMethodConfig } from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { AuthedImage } from "../../components/AuthedImage";

type Draft = {
  label: string;
  kind: string;
  account_hint: string;
  instructions: string;
  display_order: number;
};

const EMPTY_DRAFT: Draft = {
  label: "",
  kind: "QR",
  account_hint: "",
  instructions: "",
  display_order: 0,
};

export default function PaymentSettingsPage() {
  const [methods, setMethods] = useState<PaymentMethodConfig[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<PaymentMethodConfig | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [newImage, setNewImage] = useState<File | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const list = await apiFetch<PaymentMethodConfig[]>("/api/v1/payment-methods");
      setMethods([...list].sort((a, b) => a.display_order - b.display_order));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load payment methods.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function reset() {
    setEditing(null);
    setCreating(false);
    setDraft(EMPTY_DRAFT);
    setNewImage(null);
  }

  function openCreate() {
    setDraft(EMPTY_DRAFT);
    setNewImage(null);
    setCreating(true);
    setEditing(null);
    setNotice(null);
  }

  function openEdit(method: PaymentMethodConfig) {
    setDraft({
      label: method.label,
      kind: method.kind,
      account_hint: method.account_hint,
      instructions: method.instructions,
      display_order: method.display_order,
    });
    setNewImage(null);
    setEditing(method);
    setCreating(false);
    setNotice(null);
  }

  async function save() {
    if (draft.label.trim().length === 0) {
      setError("Give the method a name.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const saved = editing
        ? await apiFetch<PaymentMethodConfig>(`/api/v1/payment-methods/${editing.id}`, {
            method: "PATCH",
            body: JSON.stringify({
              label: draft.label.trim(),
              account_hint: draft.account_hint,
              instructions: draft.instructions,
              display_order: draft.display_order,
            }),
          })
        : await apiFetch<PaymentMethodConfig>("/api/v1/payment-methods", {
            method: "POST",
            body: JSON.stringify({
              label: draft.label.trim(),
              kind: draft.kind,
              account_hint: draft.account_hint,
              instructions: draft.instructions,
              display_order: draft.display_order,
              is_active: true,
            }),
          });

      if (newImage) {
        const form = new FormData();
        form.append("image", newImage);
        await apiFetch<PaymentMethodConfig>(`/api/v1/payment-methods/${saved.id}/qr-image`, {
          method: "POST",
          body: form,
        });
      }
      setNotice(editing ? "Payment method updated." : "Payment method added.");
      reset();
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save the payment method.");
    } finally {
      setBusy(false);
    }
  }

  async function replaceImage(method: PaymentMethodConfig, file: File) {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("image", file);
      await apiFetch<PaymentMethodConfig>(`/api/v1/payment-methods/${method.id}/qr-image`, {
        method: "POST",
        body: form,
      });
      setNotice(`QR image replaced for “${method.label}”.`);
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not upload the QR image.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmToggle(method: PaymentMethodConfig) {
    const next = !method.is_active;
    const verb = next ? "Enable" : "Disable";
    if (
      !window.confirm(
        `${verb} “${method.label}”? ${
          next ? "It will appear for cashiers again." : "Cashiers will no longer be able to select it."
        }`
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/payment-methods/${method.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: next }),
      });
      setNotice(next ? `“${method.label}” enabled.` : `“${method.label}” disabled.`);
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update the payment method.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete(method: PaymentMethodConfig) {
    if (
      !window.confirm(
        `Delete “${method.label}”? Past payments keep their records, but this method disappears from checkout. This cannot be undone.`
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/payment-methods/${method.id}`, { method: "DELETE" });
      setNotice(`“${method.label}” deleted.`);
      if (editing?.id === method.id) reset();
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete the payment method.");
    } finally {
      setBusy(false);
    }
  }

  const panelOpen = creating || editing !== null;
  const activeCount = methods.filter((method) => method.is_active).length;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Checkout"
        title="Payment methods"
        sub={`${methods.length} method${methods.length === 1 ? "" : "s"} · ${activeCount} active. Guests see a QR only as a way to pay — cashiers still verify the received amount before the bill is marked paid.`}
        actions={
          <button className="btn" disabled={busy || panelOpen} onClick={openCreate} type="button">
            Add method
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="settings-layout">
        <div className="stack">
          {methods.length === 0 ? (
            <div className="empty-state">
              <strong>No payment methods yet</strong>
              <span>Add cash or a QR method so cashiers can settle bills.</span>
            </div>
          ) : null}

          {methods.map((method) => (
            <section className="card method-card" key={method.id}>
              <div className="method-head">
                <div>
                  <strong>{method.label}</strong>
                  <span className={`badge ${method.kind === "CASH" ? "new" : "pending"}`}>
                    {method.kind === "CASH" ? "Cash" : "QR"}
                  </span>
                  {!method.is_active ? <span className="badge rejected">Disabled</span> : null}
                </div>
                <div className="method-actions">
                  <button
                    className="btn ghost btn-sm"
                    disabled={busy}
                    onClick={() => openEdit(method)}
                    type="button"
                  >
                    Edit
                  </button>
                </div>
              </div>

              {method.account_hint ? <p className="muted">{method.account_hint}</p> : null}
              {method.instructions ? <p className="hint">{method.instructions}</p> : null}

              {method.kind === "QR" ? (
                <div className="qr-manage">
                  {method.has_qr_image && method.qr_image_url ? (
                    <AuthedImage
                      className="qr-thumb"
                      src={method.qr_image_url}
                      alt={`${method.label} QR code preview`}
                      width={84}
                      height={84}
                    />
                  ) : null}
                  <label className="btn secondary as-label">
                    {method.has_qr_image ? "Replace image" : "Upload image"}
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      disabled={busy}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file && method.has_qr_image) {
                          if (window.confirm(`Replace the QR image for “${method.label}”?`)) {
                            void replaceImage(method, file);
                          } else {
                            event.target.value = "";
                          }
                        } else if (file) {
                          void replaceImage(method, file);
                        }
                      }}
                    />
                  </label>
                  {!method.has_qr_image ? (
                    <p className="hint">
                      No QR image yet — cashiers cannot use this method until one is uploaded.
                    </p>
                  ) : null}
                </div>
              ) : null}

              <div className="method-foot">
                <button
                  className="ghost"
                  disabled={busy}
                  onClick={() => void confirmToggle(method)}
                  type="button"
                >
                  {method.is_active ? "Disable" : "Enable"}
                </button>
                <button
                  className="ghost danger"
                  disabled={busy}
                  onClick={() => void confirmDelete(method)}
                  type="button"
                >
                  Delete
                </button>
              </div>
            </section>
          ))}
        </div>

        <aside className="settings-panel" aria-label="Payment method editor">
          {!panelOpen ? (
            <div className="empty-state">
              <strong>Nothing selected</strong>
              <span>Pick a method to edit, or add a new one.</span>
            </div>
          ) : (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void save();
              }}
            >
              <div className="menu-editor-head">
                <div>
                  <h3>{editing ? "Edit method" : "Add method"}</h3>
                  <p className="muted text-sm" style={{ margin: 0 }}>
                    {editing ? "Type cannot be changed after creation." : "Cash or a scannable QR code."}
                  </p>
                </div>
                <button className="btn ghost btn-sm" type="button" onClick={reset}>
                  Close
                </button>
              </div>

              <div className="menu-editor-body">
                <label className="field">
                  Name
                  <input
                    value={draft.label}
                    maxLength={80}
                    onChange={(event) => setDraft({ ...draft, label: event.target.value })}
                    placeholder="e.g. eSewa, IME Pay, Bank transfer"
                    required
                  />
                </label>

                <label className="field">
                  Type
                  <select
                    value={draft.kind}
                    disabled={editing !== null}
                    onChange={(event) => setDraft({ ...draft, kind: event.target.value })}
                  >
                    <option value="QR">QR code (guest scans)</option>
                    <option value="CASH">Cash</option>
                  </select>
                </label>

                <label className="field">
                  Account hint (optional)
                  <input
                    value={draft.account_hint}
                    maxLength={160}
                    onChange={(event) => setDraft({ ...draft, account_hint: event.target.value })}
                    placeholder="e.g. Merchant ID 98XXXXXXXX"
                  />
                </label>

                <label className="field">
                  Checkout instructions (optional)
                  <textarea
                    value={draft.instructions}
                    maxLength={500}
                    rows={3}
                    onChange={(event) => setDraft({ ...draft, instructions: event.target.value })}
                    placeholder="Shown to the cashier alongside the QR code"
                  />
                </label>

                <label className="field">
                  Display order
                  <input
                    type="number"
                    min={0}
                    max={1000}
                    value={draft.display_order}
                    onChange={(event) =>
                      setDraft({ ...draft, display_order: Number(event.target.value) || 0 })
                    }
                  />
                </label>

                <label className="field">
                  QR image (PNG, JPEG or WebP · up to 2 MB)
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={(event) => setNewImage(event.target.files?.[0] ?? null)}
                  />
                </label>

                <div className="page-actions">
                  <button className="btn" disabled={busy} type="submit">
                    {busy ? "Saving…" : editing ? "Save changes" : "Add method"}
                  </button>
                  <button className="btn secondary" disabled={busy} onClick={reset} type="button">
                    Cancel
                  </button>
                </div>
              </div>
            </form>
          )}
        </aside>
      </div>
    </div>
  );
}
