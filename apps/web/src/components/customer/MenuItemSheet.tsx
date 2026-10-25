import type { MenuItem } from "../../lib/api";
import { formatMoney } from "../../lib/api";
import { Sheet } from "../Sheet";

type MenuItemSheetProps = {
  item: MenuItem | null;
  quantity: number;
  onClose: () => void;
  onSetQuantity: (item: MenuItem, quantity: number) => void;
  onOpen3D: (item: MenuItem) => void;
};

export function MenuItemSheet({
  item,
  quantity,
  onClose,
  onSetQuantity,
  onOpen3D,
}: MenuItemSheetProps) {
  return (
    <Sheet open={item !== null} onClose={onClose} title={item?.name ?? "Item"} wide>
      {item ? (
        <>
          {item.image_path ? (
            <div className="item-sheet-photo">
              <img src={item.image_path} alt="" width={800} height={600} decoding="async" />
            </div>
          ) : null}

          <div className="item-sheet-head">
            <span className="item-sheet-price">
              {formatMoney(item.current_price_minor, item.currency_code)}
            </span>
          </div>

          {item.description ? <p className="item-sheet-desc">{item.description}</p> : null}

          {item.ingredients_text ? (
            <div className="item-sheet-section">
              <h3>What’s inside</h3>
              <p>{item.ingredients_text}</p>
            </div>
          ) : null}

          {item.model_path ? (
            <div style={{ marginTop: "var(--space-4)" }}>
              <button type="button" className="model-link" onClick={() => onOpen3D(item)}>
                <span aria-hidden="true">◈</span>
                View this dish in 3D
              </button>
            </div>
          ) : null}

          <div className="item-sheet-actions">
            <div className="qty" aria-label="Quantity">
              <button
                type="button"
                onClick={() => onSetQuantity(item, quantity - 1)}
                disabled={quantity === 0}
                aria-label={`Remove one ${item.name}`}
              >
                −
              </button>
              <span aria-live="polite">{quantity}</span>
              <button
                type="button"
                onClick={() => onSetQuantity(item, quantity + 1)}
                aria-label={`Add one ${item.name}`}
              >
                +
              </button>
            </div>
            <button
              type="button"
              className="btn btn-lg"
              onClick={() => {
                if (quantity === 0) onSetQuantity(item, 1);
                else onClose();
              }}
            >
              {quantity === 0
                ? "Add to order"
                : `In your order · ${formatMoney(
                    item.current_price_minor * quantity,
                    item.currency_code
                  )}`}
            </button>
          </div>
          <p className="sheet-note">
            Staff confirm every order before the kitchen starts. Prices and availability come from the
            restaurant.
          </p>
        </>
      ) : null}
    </Sheet>
  );
}
