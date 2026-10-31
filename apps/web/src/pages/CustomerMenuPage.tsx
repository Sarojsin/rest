import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { monogram } from "../lib/brand";
import {
  apiFetch,
  newIdempotencyKey,
  ApiError,
  type MenuItem,
  type PublicMenu,
  type PublicServiceCall,
} from "../lib/api";
import { Sheet } from "../components/Sheet";
import { DishCard } from "../components/customer/DishCard";
import { MenuItemSheet } from "../components/customer/MenuItemSheet";
import { CartSheet, type CartLine } from "../components/customer/CartSheet";
import { CustomerDock, type CallStatus } from "../components/customer/CustomerDock";
import { Model3DViewer } from "../components/customer/Model3DViewer";

type Cart = Record<string, CartLine>;

// How long list/acknowledge feedback stays relevant on the customer screen.
const REQUESTED_WINDOW_MS = 20 * 60 * 1000;
const ACKNOWLEDGED_WINDOW_MS = 15 * 60 * 1000;

function freshCallStatus(call: PublicServiceCall | null, now: number): CallStatus {
  if (!call) return "idle";
  const parsed = Date.parse(call.acknowledged_at ?? call.requested_at);
  if (Number.isNaN(parsed)) return "idle";
  if (call.status === "ACKNOWLEDGED") {
    return now - parsed <= ACKNOWLEDGED_WINDOW_MS ? "acknowledged" : "idle";
  }
  if (call.status === "REQUESTED") {
    return now - parsed <= REQUESTED_WINDOW_MS ? "requested" : "idle";
  }
  return "idle";
}

// How often the menu is re-fetched so admin price/availability edits reach seated guests.
const MENU_REFRESH_MS = 40_000;

// A cart survives refreshes and accidental reopens of the same table's tab. Keyed per
// table token so scanning another table never inherits the wrong order.
function cartStorageKey(qrToken: string | undefined): string | null {
  return qrToken ? `rest.cart.${qrToken}` : null;
}

type PersistedCart = {
  idempotency_key: string;
  note: string;
  lines: Array<{ menu_item_id: string; quantity: number; note: string }>;
};

function loadPersistedCart(qrToken: string): PersistedCart | null {
  try {
    const raw = sessionStorage.getItem(cartStorageKey(qrToken) ?? "");
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const data = parsed as Partial<PersistedCart>;
    if (typeof data.idempotency_key !== "string" || data.idempotency_key.length < 8) return null;
    if (!Array.isArray(data.lines)) return null;
    return {
      idempotency_key: data.idempotency_key,
      note: typeof data.note === "string" ? data.note : "",
      lines: data.lines
        .filter(
          (line) =>
            typeof line?.menu_item_id === "string" &&
            Number.isInteger(line?.quantity) &&
            (line?.quantity ?? 0) > 0
        )
        .map((line) => ({
          menu_item_id: line.menu_item_id,
          quantity: Math.min(line.quantity, 50),
          note: typeof line.note === "string" ? line.note.slice(0, 280) : "",
        })),
    };
  } catch {
    return null;
  }
}

// Cheap fingerprint so a 40s poll that returned an identical menu skips re-render entirely.
function menuFingerprint(menu: PublicMenu): string {
  return JSON.stringify({
    restaurant: menu.restaurant_name,
    currency: menu.currency_code,
    table: menu.table_display_name,
    categories: menu.categories.map((category) => ({
      id: category.id,
      name: category.name,
      description: category.description,
      status: category.status,
      items: category.items.map((item) => ({
        id: item.id,
        name: item.name,
        description: item.description,
        status: item.status,
        price: item.current_price_minor,
        currency: item.currency_code,
        emoji: item.image_emoji,
        image: item.image_path ?? "",
        model: item.model_path ?? "",
        ingredients: item.ingredients_text ?? "",
      })),
    })),
  });
}

export default function CustomerMenuPage() {
  const { qrToken } = useParams();
  const navigate = useNavigate();
  const [menu, setMenu] = useState<PublicMenu | null>(null);
  const [cart, setCart] = useState<Cart>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [sheetItem, setSheetItem] = useState<MenuItem | null>(null);
  const [model3DItem, setModel3DItem] = useState<MenuItem | null>(null);
  const [modelViewerLoaded, setModelViewerLoaded] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState(() => newIdempotencyKey());
  const [callStatus, setCallStatus] = useState<CallStatus>("idle");
  const [callBusy, setCallBusy] = useState(false);
  const [cartNotice, setCartNotice] = useState<string | null>(null);
  // Cache of the last menu fingerprint; equal fingerprint means skip setMenu (no re-render).
  const menuFingerprintRef = useRef<string | null>(null);
  // Cart restore runs exactly once, on the first menu that arrives.
  const cartLoadedRef = useRef(false);
  // Menu versions whose cart merge has already been applied.
  const cartMergedFingerprintRef = useRef<string | null>(null);

  useEffect(() => {
    if (!qrToken) return;
    const token = qrToken;
    let cancelled = false;
    // Re-fetch quietly: the first failure shows the page error, later poll failures keep
    // the menu currently on screen instead of replacing it with an error.
    async function load(showErrors: boolean) {
      try {
        const data = await apiFetch<PublicMenu>(`/api/v1/public/qr/${token}/menu`);
        if (cancelled) return;
        const nextFingerprint = menuFingerprint(data);
        if (menuFingerprintRef.current === nextFingerprint) return;
        cartMergedFingerprintRef.current = null;
        menuFingerprintRef.current = nextFingerprint;
        setMenu(data);
        if (showErrors) setError(null);
        if (!cartLoadedRef.current) {
          cartLoadedRef.current = true;
          const persisted = loadPersistedCart(token);
          if (persisted) {
            const itemsById = new Map(
              data.categories.flatMap((c) => c.items).map((item) => [item.id, item])
            );
            setCart(() => {
              const restored: Cart = {};
              for (const line of persisted.lines) {
                const item = itemsById.get(line.menu_item_id);
                if (item) restored[item.id] = { item, quantity: line.quantity, note: line.note };
              }
              return restored;
            });
            setNote(persisted.note);
            setIdempotencyKey(persisted.idempotency_key);
          }
        }
      } catch (err) {
        if (!cancelled && showErrors) {
          setError(err instanceof ApiError ? err.detail : "Menu unavailable.");
        }
      }
    }
    apiFetch<{ call: PublicServiceCall | null }>(
      `/api/v1/public/qr/${qrToken}/service-calls/latest`
    )
      .then((data) => setCallStatus(freshCallStatus(data.call, Date.now())))
      .catch(() => undefined);
    void load(true);
    const timer = window.setInterval(() => void load(false), MENU_REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [qrToken]);

  // While a service call is open, keep the guest informed of waiter acknowledgement.
  useEffect(() => {
    if (!qrToken || (callStatus !== "requested" && callStatus !== "acknowledged")) return;
    const timer = window.setInterval(() => {
      apiFetch<{ call: PublicServiceCall | null }>(
        `/api/v1/public/qr/${qrToken}/service-calls/latest`
      )
        .then((data) => {
          setCallStatus(freshCallStatus(data.call, Date.now()));
        })
        .catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [qrToken, callStatus]);

  const lines = useMemo(() => Object.values(cart).filter((line) => line.quantity > 0), [cart]);
  const subtotal = lines.reduce((sum, line) => sum + line.item.current_price_minor * line.quantity, 0);
  const itemCount = lines.reduce((sum, line) => sum + line.quantity, 0);

  // After every menu change, refresh cart line items to the current server data:
  // prices update in place, vanished items are dropped, and the guest gets a notice.
  useEffect(() => {
    if (!menu) return;
    // Skip work when the menu object identity stayed the same (no-change poll).
    const menuFingerprintNow = menuFingerprint(menu);
    if (cartMergedFingerprintRef.current === menuFingerprintNow) return;
    cartMergedFingerprintRef.current = menuFingerprintNow;
    const itemsById = new Map(menu.categories.flatMap((c) => c.items).map((item) => [item.id, item]));
    let removedCount = 0;
    let repricedCount = 0;
    const changedLines: Cart = {};
    let changed = false;
    for (const [id, line] of Object.entries(cart)) {
      const item = itemsById.get(id);
      if (!item) {
        changed = true;
        removedCount += line.quantity;
        continue;
      }
      if (item.current_price_minor !== line.item.current_price_minor) {
        repricedCount += 1;
        changed = true;
      }
      changedLines[id] = { item, quantity: line.quantity, note: line.note };
    }
    if (changed) {
      setCart(changedLines);
      setCartNotice(
        removedCount > 0
          ? `${removedCount} item${removedCount === 1 ? "" : "s"} from your order ${
              removedCount === 1 ? "is" : "are"
            } no longer on the menu.` + (repricedCount > 0 ? " Prices also changed." : "")
          : repricedCount > 0
            ? "Prices changed — your order was checked against the current menu."
            : null
      );
    }
  }, [menu, cart]);

  // Persist the cart (plus the kitchen note and the idempotency key) per table token.
  // Keyed in sessionStorage: shared across reloads of the same tab, never across tabs.
  useEffect(() => {
    const key = cartStorageKey(qrToken);
    if (!key || !cartLoadedRef.current) return;
    try {
      if (lines.length === 0) {
        sessionStorage.removeItem(key);
        return;
      }
      const payload: PersistedCart = {
        idempotency_key: idempotencyKey,
        note,
        lines: lines.map((line) => ({
          menu_item_id: line.item.id,
          quantity: line.quantity,
          note: line.note,
        })),
      };
      sessionStorage.setItem(key, JSON.stringify(payload));
    } catch {
      // Storage can be unavailable (private mode/full); the cart still works in memory.
    }
  }, [lines, note, idempotencyKey, qrToken]);

  useEffect(() => {
    if (!menu || menu.categories.length === 0) return;
    setActiveCategory(menu.categories[0].id);
  }, [menu]);

  // Track the category currently in view for the sticky chip bar.
  useEffect(() => {
    if (!menu) return;
    const sections = menu.categories
      .map((c) => document.getElementById(`cat-${c.id}`))
      .filter((el): el is HTMLElement => el !== null);
    if (sections.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (visible) setActiveCategory(visible.target.id.replace("cat-", ""));
      },
      { rootMargin: "-170px 0px -55% 0px", threshold: 0 }
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [menu]);

  // Reset the poster fade whenever a different model is opened.
  useEffect(() => {
    if (model3DItem) setModelViewerLoaded(false);
  }, [model3DItem]);

  function setQty(item: MenuItem, quantity: number) {
    setCart((prev) => {
      const next = { ...prev };
      if (quantity <= 0) delete next[item.id];
      else next[item.id] = { item, quantity, note: next[item.id]?.note ?? "" };
      return next;
    });
  }

  function scrollToCategory(id: string) {
    document.getElementById(`cat-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function sendOrder() {
    if (!qrToken || lines.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const result = await apiFetch<{ order: { id: string }; status_token: string }>(
        `/api/v1/public/qr/${qrToken}/orders`,
        {
          method: "POST",
          idempotencyKey,
          body: JSON.stringify({
            customer_note: note,
            items: lines.map((line) => ({
              menu_item_id: line.item.id,
              quantity: line.quantity,
              special_instructions: line.note,
            })),
          }),
        }
      );
      // Order is recorded server-side; drop the stored cart so a back-navigation
      // doesn't resurrect a stale order for this table's tab.
      try {
        sessionStorage.removeItem(cartStorageKey(qrToken) ?? "");
      } catch {
        // ignore storage failures
      }
      navigate(`/status/${result.status_token}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not submit the order.");
      setCartOpen(false);
    } finally {
      setBusy(false);
    }
  }

  async function callWaiter() {
    if (!qrToken || callBusy || callStatus === "requested") return;
    setCallBusy(true);
    setError(null);
    try {
      const result = await apiFetch<PublicServiceCall>(
        `/api/v1/public/qr/${qrToken}/service-calls`,
        { method: "POST" }
      );
      setCallStatus(result.status === "ACKNOWLEDGED" ? "acknowledged" : "requested");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not request a waiter.");
    } finally {
      setCallBusy(false);
    }
  }

  const searchResults = useMemo(() => {
    if (!menu) return [];
    const needle = search.trim().toLowerCase();
    if (!needle) return [];
    return menu.categories
      .flatMap((category) => category.items)
      .filter(
        (item) =>
          item.name.toLowerCase().includes(needle) ||
          (item.description ?? "").toLowerCase().includes(needle) ||
          (item.ingredients_text ?? "").toLowerCase().includes(needle)
      );
  }, [menu, search]);

  const searching = search.trim().length > 0;

  if (!menu && !error) {
    return (
      <div className="menu-shell" data-theme="customer">
        <div className="shell">
          <p className="muted">Loading menu…</p>
        </div>
      </div>
    );
  }

  if (error && !menu) {
    return (
      <div className="menu-shell" data-theme="customer">
        <div className="shell">
          <div className="error" role="alert">
            {error}
          </div>
          <Link className="btn secondary" to="/">
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  if (!menu) return null;

  return (
    <div className="menu-shell" data-theme="customer">
      <header className="menu-topbar">
        <div className="menu-topbar-inner">
          <div className="row">
            <Link className="brand" to="/">
              <div className="mark" aria-hidden="true">
                {monogram(menu.restaurant_name)}
              </div>
              <div>
                <h1>{menu.restaurant_name}</h1>
                <p>{menu.table_display_name} · Table-side menu</p>
              </div>
            </Link>
            <span className="menu-table-chip">{menu.table_display_name}</span>
          </div>
        </div>

        <div className="menu-search">
          <label className="visually-hidden" htmlFor="menu-search-input">
            Search the menu
          </label>
          <input
            id="menu-search-input"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search dishes or ingredients"
            autoComplete="off"
          />
        </div>

        {!searching && menu.categories.length > 0 ? (
          <nav className="cat-chips" aria-label="Menu categories">
            {menu.categories.map((category) => (
              <button
                key={category.id}
                type="button"
                className={`cat-chip ${activeCategory === category.id ? "is-active" : ""}`}
                onClick={() => scrollToCategory(category.id)}
              >
                {category.name}
              </button>
            ))}
          </nav>
        ) : null}
      </header>

      <main className="menu-body">
        {error ? (
          <div className="error" role="alert">
            {error}
          </div>
        ) : null}

        {cartNotice ? (
          <div className="cart-notice" role="status">
            <span aria-hidden="true">ⓘ</span>
            {cartNotice}
            <button
              type="button"
              className="cart-notice-close"
              aria-label="Dismiss menu update notice"
              onClick={() => setCartNotice(null)}
            >
              ×
            </button>
          </div>
        ) : null}

        {!searching ? (
          <div className="menu-intro">
            <p className="kicker">Welcome to {menu.restaurant_name}</p>
            <h2>What would you like tonight?</h2>
            <p>
              Browse the menu, build your order, then send it to the floor. A team member confirms
              before the kitchen begins.
            </p>
          </div>
        ) : null}

        {searching ? (
          <section className="cat-section" aria-label="Search results">
            <h2>{searchResults.length > 0 ? "Search results" : "Nothing matched"}</h2>
            <p className="muted">
              {searchResults.length > 0
                ? `${searchResults.length} dish${searchResults.length === 1 ? "" : "es"} matching “${search.trim()}”`
                : `No dishes match “${search.trim()}”. Try a shorter word.`}
            </p>
            {searchResults.length > 0 ? (
              <div className="dish-grid">
                {searchResults.map((item) => (
                  <DishCard
                    key={item.id}
                    item={item}
                    quantity={cart[item.id]?.quantity ?? 0}
                    onOpen={setSheetItem}
                    onAdd={(target) => setQty(target, 1)}
                    onDecrease={(target) => setQty(target, (cart[target.id]?.quantity ?? 0) - 1)}
                    onIncrease={(target) => setQty(target, (cart[target.id]?.quantity ?? 0) + 1)}
                  />
                ))}
              </div>
            ) : null}
          </section>
        ) : (
          menu.categories.map((category) => (
            <section id={`cat-${category.id}`} key={category.id} className="cat-section">
              <h2>{category.name}</h2>
              {category.description ? <p className="muted">{category.description}</p> : null}
              <div className="dish-grid">
                {category.items.map((item) => (
                  <DishCard
                    key={item.id}
                    item={item}
                    quantity={cart[item.id]?.quantity ?? 0}
                    onOpen={setSheetItem}
                    onAdd={(target) => setQty(target, 1)}
                    onDecrease={(target) => setQty(target, (cart[target.id]?.quantity ?? 0) - 1)}
                    onIncrease={(target) => setQty(target, (cart[target.id]?.quantity ?? 0) + 1)}
                  />
                ))}
              </div>
            </section>
          ))
        )}

        {menu.categories.length === 0 ? (
          <div className="empty-state">
            <strong>The menu is not available right now</strong>
            <span>Please ask a member of staff for help.</span>
          </div>
        ) : null}
      </main>

      <CustomerDock
        itemCount={itemCount}
        subtotal={subtotal}
        currency={menu.currency_code}
        callStatus={callStatus}
        callBusy={callBusy}
        onCallWaiter={() => void callWaiter()}
        onOpenCart={() => setCartOpen(true)}
      />

      <CartSheet
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        lines={lines}
        tableName={menu.table_display_name}
        currency={menu.currency_code}
        note={note}
        onNoteChange={setNote}
        onSetQuantity={setQty}
        onSend={() => void sendOrder()}
        busy={busy}
      />

      <MenuItemSheet
        item={sheetItem}
        quantity={sheetItem ? (cart[sheetItem.id]?.quantity ?? 0) : 0}
        onClose={() => setSheetItem(null)}
        onSetQuantity={setQty}
        onOpen3D={(item) => {
          setSheetItem(null);
          setModel3DItem(item);
        }}
      />

      <Sheet
        open={model3DItem !== null}
        onClose={() => setModel3DItem(null)}
        title={model3DItem ? `${model3DItem.name} in 3D` : "3D view"}
      >
        {model3DItem ? (
          <>
            <div className={`model-stage ${modelViewerLoaded ? "is-loaded" : ""}`}>
              <Model3DViewer item={model3DItem} onLoaded={() => setModelViewerLoaded(true)} />
              {model3DItem.image_path ? (
                <img className="model-poster" src={model3DItem.image_path} alt="" aria-hidden="true" />
              ) : null}
            </div>
            <p className="muted model-hint">Drag to look around · turns to face you automatically</p>
            <p className="hint">
              Illustration only — the plated dish may differ. Ask staff about allergens.
            </p>
          </>
        ) : null}
      </Sheet>
    </div>
  );
}
