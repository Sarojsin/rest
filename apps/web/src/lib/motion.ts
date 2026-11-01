/**
 * Customer menu motion system.
 *
 * One source of truth for timings, easings, and springs so the customer
 * experience feels consistent instead of a collection of one-off animations.
 * Every consumer must respect `prefers-reduced-motion` via `useMenuMotion`.
 */
import { useReducedMotion, type Transition, type Variants } from "framer-motion";

export const DURATION = {
  /** Button press feedback. */
  fast: 0.12,
  /** Hover / focus colour and elevation changes. */
  hover: 0.18,
  /** Card and section entrances. */
  card: 0.3,
  /** Dialogs and menus. */
  modal: 0.25,
  /** Bottom sheets. */
  sheet: 0.35,
} as const;

export const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];
export const EASE_IN: [number, number, number, number] = [0.4, 0, 1, 1];

export const SPRING_SOFT: Transition = { type: "spring", stiffness: 380, damping: 32, mass: 0.7 };
export const SPRING_SHEET: Transition = { type: "spring", stiffness: 320, damping: 32, mass: 0.9 };

export type MenuMotion = {
  reduced: boolean;
  /** Zero-duration transition for reduced-motion users. */
  none: Transition;
  fast: Transition;
  hover: Transition;
  card: Transition;
  modal: Transition;
  sheet: Transition;
  spring: Transition;
  /** Stagger container for hero copy. */
  hero: Variants;
  /** Stagger container for a dish grid. */
  grid: Variants;
};

/**
 * Use inside any component that animates. When the guest asks the OS to reduce
 * motion, entrances collapse to a simple opacity change and interactive springs
 * become instant, so nothing moves across the screen.
 */
export function useMenuMotion(): MenuMotion {
  const reduced = useReducedMotion() ?? false;

  return {
    reduced,
    none: { duration: 0 },
    fast: reduced ? { duration: 0 } : { duration: DURATION.fast, ease: EASE_OUT },
    hover: reduced ? { duration: 0 } : { duration: DURATION.hover, ease: EASE_OUT },
    card: reduced ? { duration: 0 } : { duration: DURATION.card, ease: EASE_OUT },
    modal: reduced ? { duration: 0 } : { duration: DURATION.modal, ease: EASE_OUT },
    sheet: reduced ? { duration: 0 } : SPRING_SHEET,
    spring: reduced ? { duration: 0 } : SPRING_SOFT,
    hero: {
      hidden: {},
      show: {
        transition: reduced
          ? { staggerChildren: 0, delayChildren: 0 }
          : { staggerChildren: 0.07, delayChildren: 0.04 },
      },
    },
    grid: {
      hidden: {},
      show: {
        transition: reduced
          ? { staggerChildren: 0, delayChildren: 0 }
          : { staggerChildren: 0.045, delayChildren: 0.02 },
      },
    },
  };
}

/** Shared hero item variant: soft fade + upward movement, never a large slide. */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: DURATION.card, ease: EASE_OUT } },
};

/** Shared dish card variant. */
export const cardIn: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: DURATION.card, ease: EASE_OUT } },
};

/** Fade used by overlays and status cross-fades. */
export const fade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: DURATION.modal, ease: EASE_OUT } },
  exit: { opacity: 0, transition: { duration: DURATION.fast, ease: EASE_IN } },
};
