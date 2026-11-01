import { AnimatePresence, motion } from "framer-motion";

import type { MenuItem } from "../../lib/api";
import { formatMoney } from "../../lib/api";
import { cardIn, useMenuMotion } from "../../lib/motion";

type DishCardProps = {
  item: MenuItem;
  quantity: number;
  onOpen: (item: MenuItem) => void;
  onAdd: (item: MenuItem) => void;
  onDecrease: (item: MenuItem) => void;
  onIncrease: (item: MenuItem) => void;
};

/**
 * Photography-first menu card.
 *
 * The whole upper card opens the detail sheet; the stepper and Add button stay
 * one tap away for guests who already know what they want. Availability comes
 * from the item status returned by the API — it is never inferred locally.
 */
export function DishCard({ item, quantity, onOpen, onAdd, onDecrease, onIncrease }: DishCardProps) {
  const motionPrefs = useMenuMotion();
  const available = item.status === "PUBLISHED" || item.status === "AVAILABLE";
  const emoji = item.image_emoji || item.name.slice(0, 1);

  return (
    <motion.article
      className={`dish-card${available ? "" : " is-unavailable"}`}
      variants={cardIn}
    >
      <button
        type="button"
        className="dish-open"
        onClick={() => onOpen(item)}
        aria-label={`${item.name} — ${formatMoney(item.current_price_minor, item.currency_code)}`}
      >
        <div className="dish-photo" data-emoji={emoji}>
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
            <span aria-hidden="true">{emoji}</span>
          )}
          {!available ? <span className="dish-flag is-soldout">Sold out</span> : null}
        </div>

        <div className="dish-info">
          <h3>{item.name}</h3>
          {item.description ? <p className="dish-desc">{item.description}</p> : null}
          <span className={`dish-avail${available ? "" : " is-soldout"}`}>
            <span className="dish-avail-dot" aria-hidden="true" />
            {available ? "Available now" : "Currently unavailable"}
          </span>
        </div>
      </button>

      <div className="dish-row">
        <span className="dish-price">
          {formatMoney(item.current_price_minor, item.currency_code)}
        </span>

        {!available ? (
          <button type="button" className="dish-add" disabled>
            Unavailable
          </button>
        ) : quantity === 0 ? (
          <motion.button
            type="button"
            className="dish-add"
            onClick={() => onAdd(item)}
            whileTap={motionPrefs.reduced ? undefined : { scale: 0.93 }}
            whileHover={motionPrefs.reduced ? undefined : { scale: 1.04 }}
            transition={motionPrefs.spring}
          >
            Add
          </motion.button>
        ) : (
          <div className="dish-stepper">
            <motion.button
              type="button"
              onClick={() => onDecrease(item)}
              aria-label={`Remove one ${item.name}`}
              whileTap={motionPrefs.reduced ? undefined : { scale: 0.88 }}
              transition={motionPrefs.spring}
            >
              −
            </motion.button>
            <span className="dish-stepper-qty" aria-live="polite">
              {quantity}
            </span>
            <motion.button
              type="button"
              onClick={() => onIncrease(item)}
              aria-label={`Add one ${item.name}`}
              whileTap={motionPrefs.reduced ? undefined : { scale: 0.88 }}
              transition={motionPrefs.spring}
            >
              +
            </motion.button>
          </div>
        )}
      </div>

      <AnimatePresence initial={false}>
        {quantity > 0 ? (
          <motion.span
            className="dish-count"
            key={quantity}
            initial={motionPrefs.reduced ? false : { opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={motionPrefs.reduced ? { opacity: 0 } : { opacity: 0, scale: 0.6 }}
            transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.spring}
            aria-hidden="true"
          >
            {quantity}
          </motion.span>
        ) : null}
      </AnimatePresence>
    </motion.article>
  );
}
