import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  apiFetch,
  newIdempotencyKey,
  ApiError,
  type MenuCategory,
  type MenuItem,
  type PublicMenu,
  type PublicServiceCall,
} from "../lib/api";
import { fadeUp, useMenuMotion } from "../lib/motion";
import { Sheet } from "../components/Sheet";
import { DishCard } from "../components/customer/DishCard";
import { MenuItemSheet } from "../components/customer/MenuItemSheet";
import { CartSheet, type CartLine } from "../components/customer/CartSheet";
import { FloatingCart, type CallStatus } from "../components/customer/FloatingCart";
import { MenuHero } from "../components/customer/MenuHero";
import { CategoryNav } from "../components/customer/CategoryNav";
import { MenuSkeleton } from "../components/customer/MenuSkeletons";
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
  const motionPrefs = useMenuMotion();

  const [menu, setMenu] = useState<PublicMenu | null>(null);
  const [cart, setCart] = useState<Cart>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
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
  const [reloadKey, setReloadKey] = useState(0);
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
        if (showErrors) {
          setError(null);
          setErrorStatus(null);
        }
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
          if (err instanceof ApiError) {
            setError(err.detail);
            setErrorStatus(err.status);
          } else {
            setError("Menu unavailable.");
            setErrorStatus(null);
          }
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
  }, [qrToken, reloadKey]);

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
  //
  // A scroll pass is used rather than IntersectionObserver because the chip bar
  // must stay in sync even when several sections are on screen at once, and the
  // guest should see the highlight move the moment they tap a chip.
  useEffect(() => {
    if (!menu) return;
    const ids = menu.categories.map((category) => category.id);
    if (ids.length === 0) return;
    let frame = 0;

    const update = () => {
      frame = 0;
      const marker = 112; // just under the sticky category rail
      let current = ids[0];
      for (const id of ids) {
        const section = document.getElementById(`cat-${id}`);
        if (!section) continue;
        if (section.getBoundingClientRect().top - marker <= 0) current = id;
        else break;
      }
      // The last section often cannot reach the marker on short menus.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
        current = ids[ids.length - 1];
      }
      setActiveCategory((previous) => (previous === current ? previous : current));
    };

    const schedule = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
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
    setActiveCategory(id);
    document.getElementById(`cat-${id}`)?.scrollIntoView({
      behavior: motionPrefs.reduced ? "auto" : "smooth",
      block: "start",
    });
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

  function retry() {
    // Force the next successful fetch to repaint, even if it is unchanged.
    menuFingerprintRef.current = null;
    setError(null);
    setErrorStatus(null);
    setReloadKey((key) => key + 1);
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

  const featured = useMemo(() => {
    if (!menu) return null;
    return (
      menu.categories
        .flatMap((category) => category.items)
        .find(
          (item) =>
            Boolean(item.image_path) && (item.status === "PUBLISHED" || item.status === "AVAILABLE")
        ) ?? null
    );
  }, [menu]);

  const searching = search.trim().length > 0;

  if (!menu && !error) {
    return (
      <div className="menu-shell" data-theme="customer">
        <MenuSkeleton />
      </div>
    );
  }

  if (error && !menu) {
    const expired = errorStatus === 404 || errorStatus === 410;
    const restricted = errorStatus === 401 || errorStatus === 403;
    return (
      <div className="menu-shell" data-theme="customer">
        <div className="m-state">
          <div className="m-state-card" role="alert">
            <div className="m-state-icon" aria-hidden="true">
              <StatusIcon kind={expired ? "expired" : restricted ? "lock" : "wifi"} />
            </div>
            <h1 className="m-state-title">
              {expired
                ? "This table link has expired"
                : restricted
                  ? "This menu is not available"
                  : "We couldn’t load the menu"}
            </h1>
            <p className="m-state-body">
              {expired
                ? "The QR code on your table may have been replaced. Please ask a member of staff for the current code."
                : restricted
                  ? "This link is no longer valid. Ask a member of staff to help you open the menu."
                  : "Check your connection and try again. Your table’s menu is still there — nothing has been ordered."}
            </p>
            <div className="m-state-actions">
              {!expired && !restricted ? (
                <button type="button" className="m-btn m-btn-primary" onClick={retry}>
                  Try again
                </button>
              ) : null}
              <Link className="m-btn m-btn-ghost" to="/">
                Back to home
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!menu) return null;

  return (
    <div className="menu-shell" data-theme="customer">
      <MenuHero
        menu={menu}
        search={search}
        onSearchChange={setSearch}
        onClearSearch={() => setSearch("")}
        featured={featured}
        onOpenFeatured={setSheetItem}
      />

      {!searching ? (
        <CategoryNav
          categories={menu.categories}
          activeCategory={activeCategory}
          onSelect={scrollToCategory}
        />
      ) : null}

      <main className="m-body" id="menu-main">
        {!menu.qr_ordering_enabled ? (
          <div className="m-notice" role="status">
            <span className="m-notice-icon" aria-hidden="true">
              ⓘ
            </span>
            <p>
              Ordering is paused for this table. You can still browse the menu — ask a member of
              staff to take your order.
            </p>
          </div>
        ) : null}

        {error ? (
          <div className="m-alert" role="alert">
            {error}
          </div>
        ) : null}

        <AnimatePresence initial={false}>
          {cartNotice ? (
            <motion.div
              className="m-notice"
              role="status"
              initial={motionPrefs.reduced ? false : { opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={motionPrefs.reduced ? { opacity: 0 } : { opacity: 0, y: -8 }}
              transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.card}
            >
              <span className="m-notice-icon" aria-hidden="true">
                ⓘ
              </span>
              <p>{cartNotice}</p>
              <button
                type="button"
                className="m-notice-close"
                aria-label="Dismiss menu update notice"
                onClick={() => setCartNotice(null)}
              >
                ×
              </button>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {searching ? (
          <motion.section
            className="m-section"
            aria-label="Search results"
            initial={motionPrefs.reduced ? false : "hidden"}
            animate="show"
            variants={motionPrefs.hero}
          >
            <motion.div className="m-section-head" variants={fadeUp}>
              <div className="m-section-heading">
                <span className="m-kicker">Search</span>
                <h2 className="m-section-title">“{search.trim()}”</h2>
                <p className="m-section-desc">
                  {searchResults.length > 0
                    ? `${searchResults.length} dish${searchResults.length === 1 ? "" : "es"} matched by name, description, or ingredients.`
                    : "Nothing on tonight’s menu matched that search."}
                </p>
              </div>
              <button
                type="button"
                className="m-btn m-btn-ghost"
                onClick={() => setSearch("")}
                style={{ minHeight: 40 }}
              >
                Clear
              </button>
            </motion.div>

            {searchResults.length > 0 ? (
              <DishGrid
                items={searchResults}
                cart={cart}
                onOpen={setSheetItem}
                onSetQuantity={setQty}
              />
            ) : (
              <motion.div className="m-search-empty" variants={fadeUp}>
                <strong>No dishes found</strong>
                <span>Try a shorter word, or browse the categories instead.</span>
              </motion.div>
            )}
          </motion.section>
        ) : menu.categories.length === 0 ? (
          <div className="m-state-card" style={{ margin: "0 auto" }}>
            <div className="m-state-icon" aria-hidden="true">
              <StatusIcon kind="dish" />
            </div>
            <h2 className="m-state-title">The menu is being updated</h2>
            <p className="m-state-body">
              There are no dishes available right now. Please ask a member of staff for help.
            </p>
          </div>
        ) : (
          menu.categories.map((category, index) => (
            <MenuSection
              key={category.id}
              category={category}
              index={index}
              cart={cart}
              onOpen={setSheetItem}
              onSetQuantity={setQty}
            />
          ))
        )}
      </main>

      <FloatingCart
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
        surface="menu"
        title={model3DItem ? `${model3DItem.name} in 3D` : "3D view"}
      >
        {model3DItem ? (
          <>
            <div className={`m-model-stage ${modelViewerLoaded ? "is-loaded" : ""}`}>
              <Model3DViewer
                item={model3DItem}
                onLoaded={() => setModelViewerLoaded(true)}
                fallbackImage={model3DItem.image_path}
              />
              {model3DItem.image_path ? (
                <img className="m-model-poster" src={model3DItem.image_path} alt="" aria-hidden="true" />
              ) : null}
            </div>
            <p className="m-model-hint">Drag to look around · turns to face you automatically</p>
            <p className="m-sheet-note">
              Illustration only — the plated dish may differ. Ask staff about allergens.
            </p>
          </>
        ) : null}
      </Sheet>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function MenuSection({
  category,
  index,
  cart,
  onOpen,
  onSetQuantity,
}: {
  category: MenuCategory;
  index: number;
  cart: Cart;
  onOpen: (item: MenuItem) => void;
  onSetQuantity: (item: MenuItem, quantity: number) => void;
}) {
  return (
    <section id={`cat-${category.id}`} className="m-section" aria-labelledby={`cat-title-${category.id}`}>
      <div className="m-section-head">
        <div className="m-section-heading">
          <span className="m-kicker">Menu {String(index + 1).padStart(2, "0")}</span>
          <h2 className="m-section-title" id={`cat-title-${category.id}`}>
            {category.name}
          </h2>
          {category.description ? <p className="m-section-desc">{category.description}</p> : null}
        </div>
        <span className="m-section-count" aria-hidden="true">
          {category.items.length} {category.items.length === 1 ? "dish" : "dishes"}
        </span>
      </div>

      {category.items.length > 0 ? (
        <DishGrid items={category.items} cart={cart} onOpen={onOpen} onSetQuantity={onSetQuantity} />
      ) : (
        <p className="m-empty-inline">No dishes in this section right now.</p>
      )}
    </section>
  );
}

function DishGrid({
  items,
  cart,
  onOpen,
  onSetQuantity,
}: {
  items: MenuItem[];
  cart: Cart;
  onOpen: (item: MenuItem) => void;
  onSetQuantity: (item: MenuItem, quantity: number) => void;
}) {
  const motionPrefs = useMenuMotion();

  return (
    <motion.div
      className="m-grid"
      variants={motionPrefs.grid}
      initial={motionPrefs.reduced ? false : "hidden"}
      whileInView="show"
      viewport={{ once: true, margin: "-48px" }}
    >
      {items.map((item) => (
        <DishCard
          key={item.id}
          item={item}
          quantity={cart[item.id]?.quantity ?? 0}
          onOpen={onOpen}
          onAdd={(target) => onSetQuantity(target, 1)}
          onDecrease={(target) => onSetQuantity(target, (cart[target.id]?.quantity ?? 0) - 1)}
          onIncrease={(target) => onSetQuantity(target, (cart[target.id]?.quantity ?? 0) + 1)}
        />
      ))}
    </motion.div>
  );
}

function StatusIcon({ kind }: { kind: "expired" | "lock" | "wifi" | "dish" }) {
  if (kind === "expired") {
    return (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.7" />
        <path d="M12 7.5V12l3 2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    );
  }
  if (kind === "lock") {
    return (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="5" y="10" width="14" height="10" rx="2.5" stroke="currentColor" strokeWidth="1.7" />
        <path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10" stroke="currentColor" strokeWidth="1.7" />
      </svg>
    );
  }
  if (kind === "dish") {
    return (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M4 16h16M6 16a6 6 0 0 1 12 0" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        <path d="M3 20h18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 9a12 12 0 0 1 16 0M7 12.5a8 8 0 0 1 10 0M10 16a4 4 0 0 1 4 0"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <circle cx="12" cy="19" r="1.2" fill="currentColor" />
    </svg>
  );
}
