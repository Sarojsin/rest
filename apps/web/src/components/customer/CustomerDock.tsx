import { formatMoney } from "../../lib/api";

export type CallStatus = "idle" | "requested" | "acknowledged";

type CustomerDockProps = {
  itemCount: number;
  subtotal: number;
  currency: string;
  callStatus: CallStatus;
  callBusy: boolean;
  onCallWaiter: () => void;
  onOpenCart: () => void;
};

/**
 * Single bottom dock: waiter request and cart in one anchored row, with safe-area
 * padding. Replaces the two overlapping floating buttons so nothing can cover a
 * primary action or the on-screen keyboard.
 */
export function CustomerDock({
  itemCount,
  subtotal,
  currency,
  callStatus,
  callBusy,
  onCallWaiter,
  onOpenCart,
}: CustomerDockProps) {
  const waiterLabel =
    callStatus === "requested"
      ? "Waiter requested"
      : callStatus === "acknowledged"
        ? "On the way"
        : callBusy
          ? "Calling…"
          : "Call waiter";

  return (
    <div className="dock">
      <div className="dock-inner">
        <div className="dock-status" role="status" aria-live="polite">
          <span
            className={`badge ${
              callStatus === "requested" ? "pending" : callStatus === "acknowledged" ? "ready" : "info"
            }`}
          >
            {callStatus === "requested"
              ? "Waiter requested"
              : callStatus === "acknowledged"
                ? "Waiter on the way"
                : "Table service"}
          </span>
          <span className="muted text-sm">
            {callStatus === "requested"
              ? "A team member has been notified."
              : callStatus === "acknowledged"
                ? "Someone is heading to your table."
                : "Tap the bell if you need anything."}
          </span>
        </div>

        <div className="dock-row">
          <button
            type="button"
            className={`dock-waiter ${
              callStatus === "requested"
                ? "is-requested"
                : callStatus === "acknowledged"
                  ? "is-acknowledged"
                  : ""
            }`}
            onClick={onCallWaiter}
            disabled={callStatus === "requested" || callBusy}
            aria-label={
              callStatus === "requested"
                ? "Waiter requested, a team member is on the way"
                : "Call a waiter to your table"
            }
          >
            <span className="dock-waiter-icon" aria-hidden="true">
              🔔
            </span>
            <span className="visually-hidden">{waiterLabel}</span>
          </button>

          <button
            type="button"
            className={`dock-cart ${itemCount > 0 ? "has-items" : ""}`}
            aria-expanded={false}
            aria-label={itemCount > 0 ? `Open your order: ${itemCount} items` : "Open your order"}
            onClick={onOpenCart}
          >
            <span className="dock-cart-label">Your order</span>
            <span className="dock-cart-meta">
              {itemCount > 0 ? (
                <>
                  <span className="dock-cart-count">{itemCount}</span>
                  <strong>{formatMoney(subtotal, currency)}</strong>
                </>
              ) : (
                <span>Empty</span>
              )}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
