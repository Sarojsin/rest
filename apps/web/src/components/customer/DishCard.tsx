import type { MenuItem } from "../../lib/api";
import { formatMoney } from "../../lib/api";

type DishCardProps = {
  item: MenuItem;
  quantity: number;
  onOpen: (item: MenuItem) => void;
  onAdd: (item: MenuItem) => void;
  onDecrease: (item: MenuItem) => void;
  onIncrease: (item: MenuItem) => void;
};

/**
 * Photography-first menu card. The whole card opens the detail sheet; the stepper
 * and Add button stay one tap away for guests who already know what they want.
 */
export function DishCard({ item, quantity, onOpen, onAdd, onDecrease, onIncrease }: DishCardProps) {
  return (
    <article className="dish-card">
      <button type="button" className="dish-open" onClick={() => onOpen(item)}>
        <div className="dish-photo">
          {item.image_path ? (
            <img
              src={item.image_path}
              alt={item.name}
              width={800}
              height={600}
              loading="lazy"
              decoding="async"
              onError={(event) => {
                const parent = event.currentTarget.parentElement;
                if (parent) parent.dataset.fallback = "1";
              }}
            />
          ) : (
            <span aria-hidden="true">{item.image_emoji || item.name.slice(0, 1)}</span>
          )}
        </div>
        <div className="dish-info">
          <h3>{item.name}</h3>
          {item.description ? <p className="dish-desc">{item.description}</p> : null}
          {item.ingredients_text ? <p className="dish-ingredients">{item.ingredients_text}</p> : null}
        </div>
      </button>

      <div className="dish-row">
        <span className="dish-price">{formatMoney(item.current_price_minor, item.currency_code)}</span>
        {quantity === 0 ? (
          <button type="button" className="dish-add" onClick={() => onAdd(item)}>
            Add
          </button>
        ) : (
          <div className="qty qty-oncard">
            <button
              type="button"
              onClick={() => onDecrease(item)}
              aria-label={`Remove one ${item.name}`}
            >
              −
            </button>
            <span aria-live="polite">{quantity}</span>
            <button
              type="button"
              onClick={() => onIncrease(item)}
              aria-label={`Add one ${item.name}`}
            >
              +
            </button>
          </div>
        )}
      </div>

      {quantity > 0 ? (
        <span className="dish-count" aria-hidden="true">
          {quantity}
        </span>
      ) : null}
    </article>
  );
}
