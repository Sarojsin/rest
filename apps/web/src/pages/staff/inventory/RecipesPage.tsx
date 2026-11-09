import { useCallback, useEffect, useMemo, useState } from "react";
import {
  apiFetch,
  type RecipeIngredient,
  type MenuCategory,
  type Ingredient,
  ApiError,
  formatMoney,
} from "../../../lib/api";
import { useAuth } from "../../../lib/auth";

type RecipeDraftItem = { ingredient_id: string; quantity_per_serving: number };

export default function RecipesPage() {
  const { has } = useAuth();
  const canManage = has("inventory.manage");
  const [menu, setMenu] = useState<MenuCategory[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [recipes, setRecipes] = useState<RecipeIngredient[]>([]);
  const [recipeMenuId, setRecipeMenuId] = useState("");
  const [recipeDraft, setRecipeDraft] = useState<RecipeDraftItem[]>([]);
  const [recipeItem, setRecipeItem] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [menuList, ingredientList, recipeList] = await Promise.all([
        apiFetch<MenuCategory[]>("/api/v1/menu"),
        apiFetch<Ingredient[]>("/api/v1/inventory/ingredients"),
        apiFetch<RecipeIngredient[]>("/api/v1/inventory/recipes"),
      ]);
      setMenu(menuList);
      setIngredients(ingredientList);
      setRecipes(recipeList);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load recipes.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const menuItems = useMemo(
    () => menu.flatMap((category) => category.items.map((item) => ({ ...item, category: category.name }))),
    [menu]
  );

  const ingredientById = useMemo(() => {
    const map = new Map<string, Ingredient>();
    ingredients.forEach((ing) => map.set(ing.id, ing));
    return map;
  }, [ingredients]);

  const selectedRecipes = recipes.filter((row) => row.menu_item_id === recipeMenuId);

  const totalCost = selectedRecipes.reduce((sum, row) => {
    const ing = ingredientById.get(row.ingredient_id);
    const unitCost = ing ? ing.cost_per_unit_minor : 0;
    return sum + row.quantity_per_serving * unitCost;
  }, 0);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The recipe action failed.");
    } finally {
      setBusy(false);
    }
  }

  function addRecipeItem() {
    if (!recipeItem) return;
    const existing = recipeDraft.find((entry) => entry.ingredient_id === recipeItem);
    if (existing) {
      setRecipeDraft(
        recipeDraft.map((entry) =>
          entry.ingredient_id === recipeItem
            ? { ...entry, quantity_per_serving: entry.quantity_per_serving + 1 }
            : entry
        )
      );
    } else {
      setRecipeDraft([...recipeDraft, { ingredient_id: recipeItem, quantity_per_serving: 1 }]);
    }
    setRecipeItem("");
  }

  function removeRecipeItem(index: number) {
    setRecipeDraft(recipeDraft.filter((_, i) => i !== index));
  }

  function saveRecipe() {
    if (!recipeMenuId) return;
    return run(async () => {
      await apiFetch<RecipeIngredient[]>(`/api/v1/inventory/recipes/${recipeMenuId}`, {
        method: "PUT",
        body: JSON.stringify({ items: recipeDraft }),
      });
      setRecipeDraft([]);
      return "Recipe saved.";
    });
  }

  return (
    <div className="page">
      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      <div className="toolbar">
        <div className="toolbar-group">
          <select
            className="field"
            value={recipeMenuId}
            onChange={(event) => {
              setRecipeMenuId(event.target.value);
              setRecipeDraft([]);
            }}
          >
            <option value="">Select a menu item…</option>
            {menuItems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.category} · {item.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {recipeMenuId ? (
        <>
          <section className="section-card">
            <div className="section-card-head">
              <h3>Saved recipe</h3>
              <span className="muted text-sm">Ingredients per serving</span>
            </div>
            <div className="section-card-body">
              {selectedRecipes.length === 0 ? (
                <p className="muted">No ingredients saved yet.</p>
              ) : (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ingredient</th>
                        <th className="num">Qty per serving</th>
                        <th className="num">Unit</th>
                        <th className="num">Cost/unit</th>
                        <th className="num">Line cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedRecipes.map((row) => {
                        const ingredient = ingredientById.get(row.ingredient_id);
                        const unitCost = ingredient ? ingredient.cost_per_unit_minor : 0;
                        const lineCost = row.quantity_per_serving * unitCost;
                        return (
                          <tr key={row.id}>
                            <td>{ingredient?.name ?? row.ingredient_id.slice(0, 8)}</td>
                            <td className="num">{row.quantity_per_serving}</td>
                            <td className="num">{ingredient?.unit ?? "units"}</td>
                            <td className="num">{formatMoney(unitCost, "NPR")}</td>
                            <td className="num">{formatMoney(lineCost, "NPR")}</td>
                          </tr>
                        );
                      })}
                      <tr>
                        <td colSpan={4} className="num"><strong>Total cost per serving</strong></td>
                        <td className="num"><strong>{formatMoney(totalCost, "NPR")}</strong></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>

          {canManage ? (
            <section className="section-card">
              <div className="section-card-head">
                <h3>Edit recipe</h3>
              </div>
              <div className="section-card-body">
                {recipeDraft.length === 0 ? <p className="muted">Add ingredients to the draft.</p> : null}
                {recipeDraft.map((row, index) => {
                  return (
                    <div className="grid four" key={row.ingredient_id} style={{ gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                      <label className="field">
                        Ingredient
                        <select
                          value={row.ingredient_id}
                          onChange={(event) => {
                            const next = [...recipeDraft];
                            next[index] = { ...next[index], ingredient_id: event.target.value };
                            setRecipeDraft(next);
                          }}
                        >
                          <option value="">Select…</option>
                          {ingredients.map((ingredient) => (
                            <option key={ingredient.id} value={ingredient.id}>
                              {ingredient.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="field">
                        Qty per serving
                        <input
                          type="number"
                          min={0.01}
                          step={0.01}
                          value={row.quantity_per_serving}
                          onChange={(event) => {
                            const next = [...recipeDraft];
                            next[index] = { ...next[index], quantity_per_serving: Number(event.target.value) || 0 };
                            setRecipeDraft(next);
                          }}
                        />
                      </label>
                      <button
                        type="button"
                        className="btn ghost btn-sm danger"
                        onClick={() => removeRecipeItem(index)}
                        style={{ alignSelf: "end" }}
                      >
                        Remove
                      </button>
                    </div>
                  );
                })}
                <div className="row" style={{ gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
                  <select value={recipeItem} onChange={(event) => setRecipeItem(event.target.value)}>
                    <option value="">Add ingredient…</option>
                    {ingredients.map((ingredient) => (
                      <option key={ingredient.id} value={ingredient.id}>
                        {ingredient.name}
                      </option>
                    ))}
                  </select>
                  <button className="btn ghost btn-sm" type="button" onClick={addRecipeItem} disabled={!recipeItem}>
                    Add
                  </button>
                  <button
                    className="btn"
                    type="button"
                    disabled={busy || recipeDraft.length === 0}
                    onClick={() => void saveRecipe()}
                  >
                    Save recipe
                  </button>
                </div>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
