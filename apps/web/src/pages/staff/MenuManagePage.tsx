import { useEffect, useState } from "react";
import { apiFetch, formatMoney, ApiError, type MenuCategory } from "../../lib/api";

export default function MenuManagePage() {
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setCategories(await apiFetch<MenuCategory[]>("/api/v1/menu"));
  }

  useEffect(() => {
    load().catch(() => setError("Could not load menu."));
  }, []);

  async function toggle(itemId: string, status: string) {
    const next = status === "PUBLISHED" ? "UNAVAILABLE" : "PUBLISHED";
    setError(null);
    try {
      await apiFetch(`/api/v1/menu/items/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: next }),
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed.");
    }
  }

  return (
    <div>
      <h2>Menu</h2>
      <p className="muted">Guest prices come from the published catalog. Historical order lines keep snapshots.</p>
      {error ? <div className="error">{error}</div> : null}
      {categories.map((category) => (
        <section className="panel" key={category.id} style={{ marginBottom: 16 }}>
          <h3>{category.name}</h3>
          {category.items.map((item) => (
            <div className="row" key={item.id} style={{ marginTop: 8 }}>
              <div>
                <strong>{item.name}</strong>
                <div className="muted">{item.description}</div>
                <div>{formatMoney(item.current_price_minor, item.currency_code)}</div>
              </div>
              <div>
                <span className={`badge ${item.status.toLowerCase()}`}>{item.status}</span>
                <div>
                  <button className="btn ghost" onClick={() => toggle(item.id, item.status)} type="button">
                    {item.status === "PUBLISHED" ? "Mark unavailable" : "Publish"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
