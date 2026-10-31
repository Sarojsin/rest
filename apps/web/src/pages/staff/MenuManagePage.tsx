import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch, formatMoney, ApiError, type MenuCategory, type MenuItem } from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";

/**
 * Curated publish allowlist: menu items may only reference assets that ship
 * with the website (see `public/menu/...`). Blocking arbitrary URLs keeps
 * uploaded/served images reviewed — per the web security rules.
 */
const APPROVED_IMAGES = [
  { path: "/menu/food/steam-momo.webp", label: "Steam momo" },
  { path: "/menu/food/jhol-momo.jpg", label: "Jhol momo" },
  { path: "/menu/food/veg-chowmein.webp", label: "Veg chowmein" },
  { path: "/menu/food/chicken-chowmein.webp", label: "Chicken chowmein" },
  { path: "/menu/food/chicken-leg-piece.jpg", label: "Chicken leg piece" },
  { path: "", label: "No photo" },
];

const APPROVED_MODELS = [
  { path: "", label: "No 3D model" },
  { path: "/menu/models/steam-momo.glb", label: "Momo plate" },
  { path: "/menu/models/noodles-gl.glb", label: "Noodle plate" },
  { path: "/menu/models/bowl-soup.glb", label: "Soup bowl" },
];

type Draft = {
  id: string | null;
  categoryId: string;
  name: string;
  description: string;
  price: string;
  status: string;
  ingredients: string;
  emoji: string;
  imagePath: string;
  modelPath: string;
};

function emptyDraft(categoryId = ""): Draft {
  return {
    id: null,
    categoryId,
    name: "",
    description: "",
    price: "",
    status: "DRAFT",
    ingredients: "",
    emoji: "",
    imagePath: "",
    modelPath: "",
  };
}

function draftFromItem(item: MenuItem, categoryId: string): Draft {
  return {
    id: item.id,
    categoryId,
    name: item.name,
    description: item.description ?? "",
    price: (item.current_price_minor / 100).toFixed(2),
    status: item.status,
    ingredients: item.ingredients_text ?? "",
    emoji: item.image_emoji ?? "",
    imagePath: item.image_path ?? "",
    modelPath: item.model_path ?? "",
  };
}

/** Parse a major-unit price string into integer minor units, or null when invalid. */
function parsePrice(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  if (!/^\d+(\.\d{0,2})?$/.test(trimmed)) return null;
  const [whole, fraction = ""] = trimmed.split(".");
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
}

export default function MenuManagePage() {
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const editorRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<MenuCategory[]>("/api/v1/menu");
      setCategories(data);
      setError(null);
    } catch {
      setError("Could not load the menu.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const items = useMemo(
    () => categories.flatMap((category) => category.items.map((item) => ({ item, categoryId: category.id }))),
    [categories]
  );

  const visibleCategories = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return categories;
    return categories
      .map((category) => ({
        ...category,
        items: category.items.filter(
          (item) =>
            item.name.toLowerCase().includes(needle) ||
            (item.description ?? "").toLowerCase().includes(needle)
        ),
      }))
      .filter((category) => category.items.length > 0);
  }, [categories, filter]);

  function startEdit(item: MenuItem, categoryId: string) {
    setDraft(draftFromItem(item, categoryId));
    setNotice(null);
    requestAnimationFrame(() => {
      if (window.matchMedia("(max-width: 1180px)").matches) {
        editorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }

  function startCreate() {
    setDraft(emptyDraft(categories[0]?.id ?? ""));
    setNotice(null);
    requestAnimationFrame(() => {
      if (window.matchMedia("(max-width: 1180px)").matches) {
        editorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }

  async function quickToggle(item: MenuItem) {
    setError(null);
    setNotice(null);
    const next = item.status === "PUBLISHED" ? "UNAVAILABLE" : "PUBLISHED";
    setBusy(true);
    try {
      await apiFetch(`/api/v1/menu/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: next }),
      });
      setNotice(
        next === "PUBLISHED"
          ? `${item.name} is now visible to guests.`
          : `${item.name} is hidden from the guest menu.`
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not change availability.");
    } finally {
      setBusy(false);
    }
  }

  async function save(status?: string) {
    if (!draft) return;
    const priceMinor = parsePrice(draft.price);
    if (!draft.name.trim()) {
      setError("Give the item a name before saving.");
      return;
    }
    if (priceMinor === null || priceMinor < 0) {
      setError("Enter a price with up to two decimals, for example 12.50.");
      return;
    }
    if (!draft.id && !draft.categoryId) {
      setError("Choose a category for the new item.");
      return;
    }

    const nextStatus = status ?? draft.status;
    const payload = {
      name: draft.name.trim(),
      description: draft.description,
      current_price_minor: priceMinor,
      status: nextStatus,
      ingredients_text: draft.ingredients,
      image_emoji: draft.emoji,
      image_path: draft.imagePath,
      model_path: draft.modelPath,
    };

    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (draft.id) {
        await apiFetch(`/api/v1/menu/items/${draft.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        setNotice(`Saved ${payload.name}.`);
        setDraft({ ...draft, status: nextStatus });
      } else {
        const created = await apiFetch<{ id: string }>(`/api/v1/menu/items`, {
          method: "POST",
          body: JSON.stringify({ ...payload, category_id: draft.categoryId }),
        });
        setNotice(
          nextStatus === "PUBLISHED"
            ? `${payload.name} created and published.`
            : `${payload.name} created as a draft.`
        );
        setDraft({ ...draft, id: created.id, status: nextStatus });
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save the item.");
    } finally {
      setBusy(false);
    }
  }

  const publishedCount = items.filter(({ item }) => item.status === "PUBLISHED").length;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Catalog"
        title="Menu"
        sub={
          loading
            ? "Loading the published catalog…"
            : `${items.length} item${items.length === 1 ? "" : "s"} across ${categories.length} categor${
                categories.length === 1 ? "y" : "ies"
              } · ${publishedCount} live for guests. Guest prices always come from the server.`
        }
        actions={
          <>
            <input
              className="menu-filter"
              type="search"
              placeholder="Filter items"
              aria-label="Filter menu items"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
            <button className="btn" type="button" onClick={startCreate} disabled={categories.length === 0}>
              New item
            </button>
          </>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="menu-layout">
        <div className="menu-list">
          {!loading && categories.length === 0 ? (
            <div className="empty-state">
              <strong>No menu categories yet</strong>
              <span>Categories are provisioned with the restaurant. Contact your administrator.</span>
            </div>
          ) : null}

          {visibleCategories.map((category) => (
            <section className="menu-category" key={category.id} aria-labelledby={`cat-${category.id}`}>
              <div className="menu-category-head">
                <div>
                  <h3 id={`cat-${category.id}`}>{category.name}</h3>
                  {category.description ? <p className="muted text-sm" style={{ margin: 0 }}>{category.description}</p> : null}
                </div>
                <span className="badge draft">
                  {category.items.length} item{category.items.length === 1 ? "" : "s"}
                </span>
              </div>

              {category.items.length === 0 ? (
                <p className="muted text-sm" style={{ padding: "var(--space-4)" }}>
                  Nothing in this category yet.
                </p>
              ) : null}

              {category.items.map((item) => (
                <div className="menu-row" key={item.id}>
                  <div className="menu-row-thumb">
                    {item.image_path ? (
                      <img src={item.image_path} alt="" loading="lazy" decoding="async" />
                    ) : (
                      <span aria-hidden="true">{item.image_emoji || item.name.slice(0, 1).toUpperCase()}</span>
                    )}
                  </div>
                  <div className="menu-row-main">
                    <strong>{item.name}</strong>
                    <div className="muted">{item.description || "No description"}</div>
                    <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <StatusBadge status={item.status} />
                      {item.model_path ? <span className="badge info">3D</span> : null}
                    </div>
                  </div>
                  <div className="menu-row-actions">
                    <span className="menu-row-price">
                      {formatMoney(item.current_price_minor, item.currency_code)}
                    </span>
                    <button
                      className="btn ghost btn-sm"
                      type="button"
                      onClick={() => startEdit(item, category.id)}
                      disabled={busy}
                    >
                      Edit
                    </button>
                    <button
                      className="btn ghost btn-sm"
                      type="button"
                      onClick={() => void quickToggle(item)}
                      disabled={busy}
                    >
                      {item.status === "PUBLISHED" ? "Hide" : "Publish"}
                    </button>
                  </div>
                </div>
              ))}
            </section>
          ))}

          {!loading && filter && visibleCategories.length === 0 ? (
            <div className="empty-state">
              <strong>No items match “{filter}”</strong>
              <span>Clear the filter to see the whole catalog.</span>
            </div>
          ) : null}
        </div>

        <div className="menu-editor" ref={editorRef}>
          {!draft ? (
            <div className="menu-editor-body">
              <div className="empty-state">
                <strong>Nothing selected</strong>
                <span>Choose an item to edit, or create a new one.</span>
              </div>
            </div>
          ) : (
            <>
              <div className="menu-editor-head">
                <div>
                  <h3>{draft.id ? "Edit item" : "New item"}</h3>
                  <p className="muted text-sm" style={{ margin: 0 }}>
                    {draft.id ? "Changes apply to future orders only." : "Drafts stay hidden until published."}
                  </p>
                </div>
                <button className="btn ghost btn-sm" type="button" onClick={() => setDraft(null)}>
                  Close
                </button>
              </div>

              <div className="menu-editor-body">
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void save("PUBLISHED");
                  }}
                >
                  <div className="form-section">
                    <h4>Basics</h4>
                    <label className="field">
                      Name
                      <input
                        value={draft.name}
                        maxLength={120}
                        required
                        onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                        placeholder="Steam momo"
                      />
                    </label>
                    <label className="field">
                      Description
                      <textarea
                        rows={3}
                        maxLength={500}
                        value={draft.description}
                        onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                        placeholder="Ten pleated dumplings, tomato–sesame chutney."
                      />
                    </label>
                    <div className="form-grid-2">
                      <label className="field">
                        Price (major units)
                        <input
                          inputMode="decimal"
                          value={draft.price}
                          onChange={(event) => setDraft({ ...draft, price: event.target.value })}
                          placeholder="12.50"
                          required
                        />
                      </label>
                      <label className="field">
                        Category
                        <select
                          value={draft.categoryId}
                          disabled={Boolean(draft.id)}
                          onChange={(event) => setDraft({ ...draft, categoryId: event.target.value })}
                        >
                          {categories.map((category) => (
                            <option key={category.id} value={category.id}>
                              {category.name}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    {draft.id ? (
                      <p className="field-hint">Category cannot be changed after creation.</p>
                    ) : null}
                  </div>

                  <div className="form-section">
                    <h4>Guest photo</h4>
                    <p className="form-section-desc">
                      Only approved, pre-optimised photos can be attached. Uploads are managed outside this
                      screen.
                    </p>
                    <div className="image-picker">
                      {APPROVED_IMAGES.map((image) => (
                        <button
                          key={image.path || "none"}
                          type="button"
                          className="image-option"
                          aria-pressed={draft.imagePath === image.path}
                          onClick={() => setDraft({ ...draft, imagePath: image.path })}
                        >
                          {image.path ? (
                            <img src={image.path} alt="" loading="lazy" decoding="async" />
                          ) : (
                            <span className="image-placeholder" aria-hidden="true">
                              —
                            </span>
                          )}
                          {image.label}
                        </button>
                      ))}
                    </div>
                    <label className="field" style={{ marginTop: "var(--space-3)" }}>
                      Fallback emoji
                      <input
                        value={draft.emoji}
                        maxLength={8}
                        onChange={(event) => setDraft({ ...draft, emoji: event.target.value })}
                        placeholder="🥟"
                      />
                    </label>
                    <label className="field">
                      Optional 3D model
                      <select
                        value={draft.modelPath}
                        onChange={(event) => setDraft({ ...draft, modelPath: event.target.value })}
                      >
                        {APPROVED_MODELS.map((model) => (
                          <option key={model.path || "none"} value={model.path}>
                            {model.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <div className="form-section">
                    <h4>Ingredients &amp; allergens</h4>
                    <p className="form-section-desc">Shown to guests under “What’s inside”.</p>
                    <label className="field">
                      Ingredients
                      <textarea
                        rows={2}
                        maxLength={500}
                        value={draft.ingredients}
                        onChange={(event) => setDraft({ ...draft, ingredients: event.target.value })}
                        placeholder="Wheat noodles, egg, soy sauce. Contains: gluten, egg, soy."
                      />
                    </label>
                  </div>

                  <div className="sticky-bar">
                    <div className="sticky-meta">
                      <span>
                        Status: <strong>{draft.status === "PUBLISHED" ? "Published" : draft.status === "DRAFT" ? "Draft" : "Unavailable"}</strong>
                      </span>
                      <span>{draft.id ? "Editing an existing item" : "New item"}</span>
                    </div>
                    <div className="page-actions">
                      <button
                        className="btn secondary"
                        type="button"
                        disabled={busy}
                        onClick={() => void save("DRAFT")}
                      >
                        Save draft
                      </button>
                      <button className="btn" type="submit" disabled={busy}>
                        {draft.id ? "Save & publish" : "Publish"}
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
