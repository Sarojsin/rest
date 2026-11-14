import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

type SheetProps = {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  wide?: boolean;
  /** Optional element rendered below the scroll area (e.g. a sticky action row). */
  footer?: ReactNode;
  /** Show the drag handle affordance. */
  grabber?: boolean;
  /** Optional visual surface key. The customer menu uses "menu" for its theme. */
  surface?: string;
};

/**
 * Accessible bottom sheet used by customer and staff surfaces.
 * Portal-rendered so fixed positioning is never trapped by a transformed parent.
 * Locks background scroll, traps focus, closes on Escape, and restores focus.
 * Motion handles the entrance/exit; the dialog stays keyboard-accessible
 * throughout.
 */
export function Sheet({
  open,
  onClose,
  title,
  children,
  wide,
  footer,
  grabber = true,
  surface,
}: SheetProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<HTMLSpanElement>(null);
  // Callers usually pass an inline arrow function, so `onClose` has a new
  // identity on every render. Keeping it in a ref lets the focus-trap effect
  // depend only on `open`; otherwise each parent re-render re-ran the trap and
  // moved focus to the sheet's first focusable element (the close button),
  // making text inputs lose focus mid-typing.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);
  const titleId = useId();
  const reducedMotion = useReducedMotion() ?? false;
  // The portal lands on <body>, outside the layout's [data-theme] root, so the
  // sheet would otherwise inherit :root (customer) tokens on staff screens.
  // A hidden marker inside the themed tree tells us which theme to re-apply.
  const [theme, setTheme] = useState<string | null>(
    () => document.querySelector("[data-theme]")?.getAttribute("data-theme") ?? null
  );

  useEffect(() => {
    if (!open) return;
    const scope = markerRef.current?.closest("[data-theme]");
    setTheme(scope?.getAttribute("data-theme") ?? null);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const first =
      dialog?.querySelector<HTMLElement>("[data-autofocus]") ??
      dialog?.querySelector<HTMLElement>(FOCUSABLE) ??
      dialog;
    first?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const items = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null
      );
      if (items.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === firstItem || active === dialog)) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && active === lastItem) {
        event.preventDefault();
        firstItem.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [open]);

  return (
    <>
      <span ref={markerRef} hidden aria-hidden="true" />
      {createPortal(
        <AnimatePresence>
          {open ? (
            <motion.div
              className="sheet-backdrop"
              data-theme={theme ?? undefined}
              data-surface={surface}
              onClick={onClose}
              initial={reducedMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={reducedMotion ? { duration: 0 } : { duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            >
              <motion.div
                ref={dialogRef}
                className={`sheet${wide ? " sheet-wide" : ""}`}
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                tabIndex={-1}
                onClick={(event) => event.stopPropagation()}
                initial={reducedMotion ? false : { opacity: 0, y: 48, scale: 0.995 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 32 }}
                transition={
                  reducedMotion
                    ? { duration: 0 }
                    : { type: "spring", stiffness: 320, damping: 32, mass: 0.9 }
                }
              >
                {grabber ? <div className="sheet-grabber" aria-hidden="true" /> : null}
                <div className="sheet-head">
                  <h3 id={titleId}>{title}</h3>
                  <button type="button" className="sheet-close" aria-label="Close" onClick={onClose}>
                    ×
                  </button>
                </div>
                {children}
                {footer}
              </motion.div>
            </motion.div>
          ) : null}
        </AnimatePresence>,
        document.body
      )}
    </>
  );
}
