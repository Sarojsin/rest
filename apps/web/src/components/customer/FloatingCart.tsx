import { AnimatePresence, motion, useAnimationControls } from "framer-motion";
import { useEffect, useRef } from "react";

import { formatMoney } from "../../lib/api";
import { DURATION, EASE_OUT, useMenuMotion } from "../../lib/motion";

export type CallStatus = "idle" | "requested" | "acknowledged";

type FloatingCartProps = {
  itemCount: number;
  subtotal: number;
  currency: string;
  callStatus: CallStatus;
  callBusy: boolean;
  onCallWaiter: () => void;
  onOpenCart: () => void;
};

/**
 * Bottom dock for the table session.
 *
 * An empty cart must not show a checkout bar, so only the waiter control is
 * visible until the first dish is added. Adding a dish briefly pulses the cart
 * (never loops) and swaps the count with a small motion key.
 */
export function FloatingCart({
  itemCount,
  subtotal,
  currency,
  callStatus,
  callBusy,
  onCallWaiter,
  onOpenCart,
}: FloatingCartProps) {
  const motionPrefs = useMenuMotion();
  const controls = useAnimationControls();
  const previousCount = useRef(itemCount);
  const hasItems = itemCount > 0;

  useEffect(() => {
    // Only react to additions, and never animate on the initial mount.
    if (itemCount > previousCount.current && !motionPrefs.reduced) {
      void controls.start({
        scale: [1, 1.035, 1],
        transition: { duration: DURATION.card, ease: EASE_OUT },
      });
    }
    previousCount.current = itemCount;
  }, [itemCount, controls, motionPrefs.reduced]);

  const waiterLabel =
    callStatus === "requested"
      ? "Waiter requested"
      : callStatus === "acknowledged"
        ? "Waiter on the way"
        : callBusy
          ? "Calling…"
          : "Call waiter";

  const waiterState = callBusy ? "" : callStatus === "requested" ? "is-requested" : callStatus === "acknowledged" ? "is-acknowledged" : "";

  return (
    <div className="m-dock">
      <div className="m-dock-inner">
        <AnimatePresence mode="popLayout" initial={false}>
          {hasItems ? (
            <motion.div
              key="cart"
              className="m-cartbar"
              initial={motionPrefs.reduced ? false : { opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={motionPrefs.reduced ? { opacity: 0 } : { opacity: 0, y: 14 }}
              transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.card}
            >
              <motion.button
                type="button"
                className="m-cartbar-main"
                onClick={onOpenCart}
                animate={controls}
                whileTap={motionPrefs.reduced ? undefined : { scale: 0.99 }}
                aria-label={`View your order — ${itemCount} item${itemCount === 1 ? "" : "s"}, ${formatMoney(subtotal, currency)}`}
              >
                <span className="m-cartbar-icon" aria-hidden="true">
                  <CartIcon />
                </span>
                <span className="m-cartbar-count" aria-hidden="true">
                  <AnimatePresence mode="popLayout" initial={false}>
                    <motion.span
                      key={itemCount}
                      initial={motionPrefs.reduced ? false : { opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={motionPrefs.reduced ? { opacity: 0 } : { opacity: 0, y: -8 }}
                      transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.fast}
                    >
                      {itemCount}
                    </motion.span>
                  </AnimatePresence>
                </span>
                <span className="m-cartbar-label">
                  <strong>Your order</strong>
                  <span>
                    {itemCount} item{itemCount === 1 ? "" : "s"} · staff confirm before cooking
                  </span>
                </span>
                <motion.span
                  className="m-cartbar-total"
                  key={`total-${subtotal}`}
                  initial={motionPrefs.reduced ? false : { opacity: 0.4 }}
                  animate={{ opacity: 1 }}
                  transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.hover}
                >
                  {formatMoney(subtotal, currency)}
                </motion.span>
                <span className="m-cartbar-cta">
                  <span className="m-cartbar-cta-text">View cart</span>
                  <span aria-hidden="true">→</span>
                </span>
              </motion.button>

              <button
                type="button"
                className={`m-waiter ${waiterState}`}
                onClick={onCallWaiter}
                disabled={callBusy || callStatus === "requested"}
                aria-label={waiterLabel}
                title={waiterLabel}
              >
                <BellIcon />
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              className="m-dock-empty"
              initial={motionPrefs.reduced ? false : { opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={motionPrefs.reduced ? { opacity: 0 } : { opacity: 0, y: 10 }}
              transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.card}
            >
              <button
                type="button"
                className={`m-waiter ${waiterState}`}
                onClick={onCallWaiter}
                disabled={callBusy || callStatus === "requested"}
                aria-label={waiterLabel}
              >
                <BellIcon />
                <span>{waiterLabel}</span>
              </button>
              <div className="m-dock-status" role="status" aria-live="polite">
                <strong>
                  {callStatus === "requested"
                    ? "A team member has been notified"
                    : callStatus === "acknowledged"
                      ? "Someone is heading to your table"
                      : "Table service"}
                </strong>
                <span>
                  {callStatus === "idle"
                    ? "Tap the bell if you need anything. Add dishes to start an order."
                    : "This message updates automatically."}
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function CartIcon() {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 4h2.2l2.1 10.4a2 2 0 0 0 2 1.6h7.9a2 2 0 0 0 2-1.6L21 7H6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="10" cy="20" r="1.4" fill="currentColor" />
      <circle cx="18" cy="20" r="1.4" fill="currentColor" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M18 9a6 6 0 1 0-12 0c0 4-1.5 5.5-1.5 5.5h15S18 13 18 9Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M10 18.5a2.2 2.2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
