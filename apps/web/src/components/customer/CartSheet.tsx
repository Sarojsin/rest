import { AnimatePresence, motion } from "framer-motion";

import type { MenuItem } from "../../lib/api";
import { formatMoney } from "../../lib/api";
import { useMenuMotion } from "../../lib/motion";
import { Sheet } from "../Sheet";

export type CartLine = { item: MenuItem; quantity: number; note: string };

type CartSheetProps = {
  open: boolean;
  onClose: () => void;
  lines: CartLine[];
  tableName: string | null;
  currency: string;
  note: string;
  onNoteChange: (note: string) => void;
  onSetQuantity: (item: MenuItem, quantity: number) => void;
  onSend: () => void;
  busy: boolean;
};

/**
 * Cart review. Presentation only — quantities, notes, the 280-character limit,
 * and the send action are the same behaviours the page already owns.
 */
export function CartSheet({
  open,
  onClose,
  lines,
  tableName,
  currency,
  note,
  onNoteChange,
  onSetQuantity,
  onSend,
  busy,
}: CartSheetProps) {
  const motionPrefs = useMenuMotion();
  const itemCount = lines.reduce((total, line) => total + line.quantity, 0);
  const subtotal = lines.reduce((total, line) => total + line.item.current_price_minor * line.quantity, 0);

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Your order"
      surface="menu"
      footer={
        lines.length === 0 ? undefined : (
          <div className="m-cart-footer">
            <div className="m-cart-footer-meta">
              <span>
                {itemCount} item{itemCount === 1 ? "" : "s"} · staff confirm before cooking
              </span>
              <strong>{formatMoney(subtotal, currency)}</strong>
            </div>
            <motion.button
              type="button"
              className="m-btn m-btn-primary"
              disabled={busy}
              onClick={onSend}
              whileTap={motionPrefs.reduced ? undefined : { scale: 0.98 }}
              transition={motionPrefs.spring}
            >
              {busy ? "Sending…" : "Send to staff"}
            </motion.button>
          </div>
        )
      }
    >
      {lines.length === 0 ? (
        <div className="m-cart-empty">
          <span className="m-cart-empty-icon" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path
                d="M3 4h2.2l2.1 10.4a2 2 0 0 0 2 1.6h7.9a2 2 0 0 0 2-1.6L21 7H6"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="10" cy="20" r="1.3" fill="currentColor" />
              <circle cx="18" cy="20" r="1.3" fill="currentColor" />
            </svg>
          </span>
          <strong>Your order is empty</strong>
          <span>Add a dish from the menu and it will appear here, ready to review.</span>
        </div>
      ) : (
        <>
          {tableName ? (
            <p className="m-sheet-note" style={{ marginTop: 0 }}>
              {tableName} · staff confirm before the kitchen starts
            </p>
          ) : null}

          <ul className="m-cart-lines">
            <AnimatePresence initial={false}>
              {lines.map((line) => (
                <motion.li
                  key={line.item.id}
                  className="m-cart-line"
                  layout={motionPrefs.reduced ? false : true}
                  initial={motionPrefs.reduced ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={motionPrefs.reduced ? { opacity: 0 } : { opacity: 0, x: -12 }}
                  transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.card}
                >
                  <div className="m-cart-line-photo" aria-hidden="true">
                    {line.item.image_path ? (
                      <img src={line.item.image_path} alt="" loading="lazy" decoding="async" />
                    ) : (
                      line.item.image_emoji || line.item.name.slice(0, 1)
                    )}
                  </div>

                  <div className="m-cart-line-main">
                    <strong>{line.item.name}</strong>
                    <span>{formatMoney(line.item.current_price_minor, line.item.currency_code)}</span>
                    {line.note ? (
                      <span style={{ display: "block" }}>Note: {line.note}</span>
                    ) : null}
                  </div>

                  <div className="dish-stepper">
                    <motion.button
                      type="button"
                      onClick={() => onSetQuantity(line.item, line.quantity - 1)}
                      aria-label={`Remove one ${line.item.name}`}
                      whileTap={motionPrefs.reduced ? undefined : { scale: 0.88 }}
                      transition={motionPrefs.spring}
                    >
                      −
                    </motion.button>
                    <span className="dish-stepper-qty" aria-live="polite">
                      {line.quantity}
                    </span>
                    <motion.button
                      type="button"
                      onClick={() => onSetQuantity(line.item, line.quantity + 1)}
                      aria-label={`Add one ${line.item.name}`}
                      whileTap={motionPrefs.reduced ? undefined : { scale: 0.88 }}
                      transition={motionPrefs.spring}
                    >
                      +
                    </motion.button>
                  </div>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>

          <label className="m-cart-note-field">
            <span>Note for the kitchen</span>
            <textarea
              data-autofocus
              value={note}
              onChange={(event) => onNoteChange(event.target.value)}
              maxLength={280}
              rows={2}
              placeholder="Spice level, allergies, anything else"
            />
          </label>

          <p className="m-sheet-note">
            Tax is added by the restaurant when staff confirm. Food is not prepared until a waiter
            confirms your request.
          </p>
        </>
      )}
    </Sheet>
  );
}
