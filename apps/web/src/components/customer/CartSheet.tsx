import type { MenuItem } from "../../lib/api";
import { formatMoney } from "../../lib/api";
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
  const itemCount = lines.reduce((total, line) => total + line.quantity, 0);
  const subtotal = lines.reduce((total, line) => total + line.item.current_price_minor * line.quantity, 0);

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Your order"
      footer={
        lines.length === 0 ? undefined : (
          <div className="item-sheet-actions" style={{ marginTop: "var(--space-3)" }}>
            <div>
              <div className="muted text-sm">
                {itemCount} item{itemCount === 1 ? "" : "s"}
              </div>
              <strong className="numeric">{formatMoney(subtotal, currency)}</strong>
            </div>
            <button className="btn btn-lg" type="button" disabled={busy} onClick={onSend}>
              {busy ? "Sending…" : "Send to staff"}
            </button>
          </div>
        )
      }
    >
      {lines.length === 0 ? (
        <p className="muted sheet-empty">Your order is empty. Add something from the menu.</p>
      ) : (
        <>
          {tableName ? (
            <p className="muted text-sm">{tableName} · staff confirm before the kitchen starts</p>
          ) : null}

          <ul className="sheet-lines">
            {lines.map((line) => (
              <li key={line.item.id}>
                <div className="sheet-line-photo" aria-hidden="true">
                  {line.item.image_path ? (
                    <img src={line.item.image_path} alt="" loading="lazy" decoding="async" />
                  ) : (
                    line.item.image_emoji || line.item.name.slice(0, 1)
                  )}
                </div>
                <div className="sheet-line-main">
                  <strong>{line.item.name}</strong>
                  <span className="muted">
                    {formatMoney(line.item.current_price_minor, line.item.currency_code)}
                  </span>
                </div>
                <div className="qty">
                  <button
                    type="button"
                    onClick={() => onSetQuantity(line.item, line.quantity - 1)}
                    aria-label={`Remove one ${line.item.name}`}
                  >
                    −
                  </button>
                  <span aria-live="polite">{line.quantity}</span>
                  <button
                    type="button"
                    onClick={() => onSetQuantity(line.item, line.quantity + 1)}
                    aria-label={`Add one ${line.item.name}`}
                  >
                    +
                  </button>
                </div>
              </li>
            ))}
          </ul>

          <label className="field">
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

          <p className="sheet-note">
            Tax is added by the restaurant when staff confirm. Food is not prepared until a waiter
            confirms your request.
          </p>
        </>
      )}
    </Sheet>
  );
}
