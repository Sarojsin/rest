import { useCallback, useEffect, useState } from "react";
import { apiFetch, type Supplier, ApiError } from "../../../lib/api";
import { useAuth } from "../../../lib/auth";

type SupplierDraft = {
  name: string;
  contact_name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  tax_id: string;
  notes: string;
};

const EMPTY_SUPPLIER: SupplierDraft = {
  name: "",
  contact_name: "",
  email: "",
  phone: "",
  address: "",
  city: "",
  state: "",
  postal_code: "",
  country: "",
  tax_id: "",
  notes: "",
};

export default function SuppliersPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [supplierDraft, setSupplierDraft] = useState<SupplierDraft>(EMPTY_SUPPLIER);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const supplierList = await apiFetch<Supplier[]>("/api/v1/inventory/suppliers");
      setSuppliers(supplierList);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load suppliers.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The supplier action failed.");
    } finally {
      setBusy(false);
    }
  }

  function createSupplier() {
    return run(async () => {
      await apiFetch<Supplier>("/api/v1/inventory/suppliers", {
        method: "POST",
        body: JSON.stringify({
          name: supplierDraft.name.trim(),
          contact_name: supplierDraft.contact_name.trim() || null,
          email: supplierDraft.email.trim() || null,
          phone: supplierDraft.phone.trim() || null,
          address: supplierDraft.address.trim() || null,
          city: supplierDraft.city.trim() || null,
          state: supplierDraft.state.trim() || null,
          postal_code: supplierDraft.postal_code.trim() || null,
          country: supplierDraft.country.trim() || null,
          tax_id: supplierDraft.tax_id.trim() || null,
          notes: supplierDraft.notes.trim() || null,
        }),
      });
      setSupplierDraft(EMPTY_SUPPLIER);
      return "Supplier added.";
    });
  }

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Contact</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Location</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {suppliers.length === 0 ? (
              <tr>
                <td colSpan={6} className="muted text-sm" style={{ textAlign: "center", padding: "var(--space-6)" }}>
                  No suppliers yet.
                </td>
              </tr>
            ) : (
              suppliers.map((supplier) => (
                <tr key={supplier.id}>
                  <td>
                    <strong>{supplier.name}</strong>
                  </td>
                  <td className="muted text-sm">{supplier.contact_name || "—"}</td>
                  <td className="muted text-sm">{supplier.email || "—"}</td>
                  <td className="muted text-sm">{supplier.phone || "—"}</td>
                  <td className="muted text-sm">
                    {[supplier.city, supplier.state, supplier.country].filter(Boolean).join(", ") || "—"}
                  </td>
                  <td>
                    <span className="badge accepted">{supplier.is_active ? "Active" : "Inactive"}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {canManage ? (
        <section className="section-card">
          <div className="section-card-head">
            <h3>Add supplier</h3>
          </div>
          <div className="section-card-body">
            <form
              className="stack"
              onSubmit={(event) => {
                event.preventDefault();
                void createSupplier();
              }}
            >
              <div className="grid three">
                <label className="field">
                  Name
                  <input
                    value={supplierDraft.name}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, name: event.target.value })}
                    required
                  />
                </label>
                <label className="field">
                  Contact name
                  <input
                    value={supplierDraft.contact_name}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, contact_name: event.target.value })}
                  />
                </label>
                <label className="field">
                  Email
                  <input
                    type="email"
                    value={supplierDraft.email}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, email: event.target.value })}
                  />
                </label>
                <label className="field">
                  Phone
                  <input
                    value={supplierDraft.phone}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, phone: event.target.value })}
                  />
                </label>
                <label className="field">
                  Address
                  <input
                    value={supplierDraft.address}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, address: event.target.value })}
                  />
                </label>
                <label className="field">
                  City / State / Country
                  <div className="grid three" style={{ marginTop: "var(--space-1)" }}>
                    <input
                      value={supplierDraft.city}
                      onChange={(event) => setSupplierDraft({ ...supplierDraft, city: event.target.value })}
                      placeholder="City"
                    />
                    <input
                      value={supplierDraft.state}
                      onChange={(event) => setSupplierDraft({ ...supplierDraft, state: event.target.value })}
                      placeholder="State"
                    />
                    <input
                      value={supplierDraft.country}
                      onChange={(event) => setSupplierDraft({ ...supplierDraft, country: event.target.value })}
                      placeholder="Country"
                    />
                  </div>
                </label>
                <label className="field">
                  Postal code
                  <input
                    value={supplierDraft.postal_code}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, postal_code: event.target.value })}
                  />
                </label>
                <label className="field">
                  Tax ID
                  <input
                    value={supplierDraft.tax_id}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, tax_id: event.target.value })}
                  />
                </label>
                <label className="field">
                  Notes
                  <textarea
                    value={supplierDraft.notes}
                    onChange={(event) => setSupplierDraft({ ...supplierDraft, notes: event.target.value })}
                    style={{ minHeight: 96 }}
                  />
                </label>
              </div>
              <button className="btn secondary" type="submit" disabled={busy || !supplierDraft.name.trim()}>
                Add supplier
              </button>
            </form>
          </div>
        </section>
      ) : null}
    </div>
  );
}
