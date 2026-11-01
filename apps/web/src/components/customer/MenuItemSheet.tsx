import { AnimatePresence, motion } from "framer-motion";

import type { MenuItem } from "../../lib/api";
import { formatMoney } from "../../lib/api";
import { useMenuMotion } from "../../lib/motion";
import { Sheet } from "../Sheet";

type MenuItemSheetProps = {
  item: MenuItem | null;
  quantity: number;
  onClose: () => void;
  onSetQuantity: (item: MenuItem, quantity: number) => void;
  onOpen3D: (item: MenuItem) => void;
};

const section = (delay: number) => ({
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: {
    duration: 0.3,
    ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
    delay,
  },
});

/**
 * Dish detail. Mobile sees a bottom sheet; from 900px the shared Sheet becomes
 * a centred dialog. Content enters progressively, but the actions are usable
 * immediately because they are never gated behind an animation.
 */
export function MenuItemSheet({
  item,
  quantity,
  onClose,
  onSetQuantity,
  onOpen3D,
}: MenuItemSheetProps) {
  const motionPrefs = useMenuMotion();
  const available = item ? item.status === "PUBLISHED" || item.status === "AVAILABLE" : true;

  return (
    <Sheet
      open={item !== null}
      onClose={onClose}
      title={item?.name ?? "Item"}
      wide
      surface="menu"
      footer={
        item ? (
          <div className="m-sheet-actions">
            <div className="m-sheet-stepper" aria-label="Quantity">
              <motion.button
                type="button"
                onClick={() => onSetQuantity(item, quantity - 1)}
                disabled={quantity === 0}
                aria-label={`Remove one ${item.name}`}
                whileTap={motionPrefs.reduced ? undefined : { scale: 0.9 }}
                transition={motionPrefs.spring}
              >
                −
              </motion.button>
              <span className="m-sheet-stepper-qty" aria-live="polite">
                <AnimatePresence mode="popLayout" initial={false}>
                  <motion.span
                    key={quantity}
                    initial={motionPrefs.reduced ? false : { opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={motionPrefs.reduced ? { opacity: 0 } : { opacity: 0, y: -6 }}
                    transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.fast}
                  >
                    {quantity}
                  </motion.span>
                </AnimatePresence>
              </span>
              <motion.button
                type="button"
                onClick={() => onSetQuantity(item, quantity + 1)}
                aria-label={`Add one ${item.name}`}
                whileTap={motionPrefs.reduced ? undefined : { scale: 0.9 }}
                transition={motionPrefs.spring}
              >
                +
              </motion.button>
            </div>

            <motion.button
              type="button"
              className="m-btn m-btn-primary"
              onClick={() => {
                if (quantity === 0) onSetQuantity(item, 1);
                else onClose();
              }}
              whileTap={motionPrefs.reduced ? undefined : { scale: 0.98 }}
              transition={motionPrefs.spring}
              disabled={!available}
            >
              {!available
                ? "Currently unavailable"
                : quantity === 0
                  ? "Add to order"
                  : `In your order · ${formatMoney(
                      item.current_price_minor * quantity,
                      item.currency_code
                    )}`}
            </motion.button>
          </div>
        ) : undefined
      }
    >
      {item ? (
        <>
          {item.image_path ? (
            <motion.div
              className="m-sheet-photo"
              initial={motionPrefs.reduced ? false : { opacity: 0, scale: 0.985 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={motionPrefs.reduced ? motionPrefs.none : motionPrefs.card}
            >
              <img src={item.image_path} alt={item.name} width={800} height={600} decoding="async" />
            </motion.div>
          ) : null}

          <motion.div
            className="m-sheet-head"
            {...(motionPrefs.reduced ? {} : section(0.06))}
          >
            <span className="m-sheet-price">
              {formatMoney(item.current_price_minor, item.currency_code)}
            </span>
            <span className={`dish-avail${available ? "" : " is-soldout"}`}>
              <span className="dish-avail-dot" aria-hidden="true" />
              {available ? "Available now" : "Currently unavailable"}
            </span>
          </motion.div>

          {item.description ? (
            <motion.p
              className="m-sheet-desc"
              {...(motionPrefs.reduced ? {} : section(0.1))}
            >
              {item.description}
            </motion.p>
          ) : null}

          {item.ingredients_text ? (
            <motion.div
              className="m-sheet-section"
              {...(motionPrefs.reduced ? {} : section(0.14))}
            >
              <h3>What’s inside</h3>
              <p>{item.ingredients_text}</p>
            </motion.div>
          ) : null}

          {item.model_path ? (
            <motion.div {...(motionPrefs.reduced ? {} : section(0.18))} style={{ marginTop: 16 }}>
              <button type="button" className="model-link" onClick={() => onOpen3D(item)}>
                <span aria-hidden="true">◈</span>
                View this dish in 3D
              </button>
            </motion.div>
          ) : null}

          <p className="m-sheet-note">
            Staff confirm every order before the kitchen starts. Prices and availability come from
            the restaurant.
          </p>
        </>
      ) : null}
    </Sheet>
  );
}
