import { motion } from "framer-motion";
import { useEffect, useRef } from "react";

import type { MenuCategory } from "../../lib/api";
import { useMenuMotion } from "../../lib/motion";

type CategoryNavProps = {
  categories: MenuCategory[];
  activeCategory: string | null;
  onSelect: (categoryId: string) => void;
};

/**
 * Sticky category rail. The active pill is a shared layout element, so the
 * highlight slides between chips instead of blinking. The rail also keeps the
 * active chip centred as the guest scrolls the menu. `scrollToCategory` lives
 * in the page and is called from here.
 */
export function CategoryNav({ categories, activeCategory, onSelect }: CategoryNavProps) {
  const motionPrefs = useMenuMotion();
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeCategory) return;
    const scroller = scrollerRef.current;
    if (!scroller) return;
    const chip = scroller.querySelector<HTMLElement>(`[data-category="${activeCategory}"]`);
    if (!chip) return;
    const scrollerRect = scroller.getBoundingClientRect();
    const chipRect = chip.getBoundingClientRect();
    const target =
      scroller.scrollLeft + chipRect.left - scrollerRect.left - (scrollerRect.width - chipRect.width) / 2;
    scroller.scrollTo({
      left: Math.max(0, target),
      behavior: motionPrefs.reduced ? "auto" : "smooth",
    });
  }, [activeCategory, motionPrefs.reduced]);

  if (categories.length === 0) return null;

  return (
    <nav className="m-catnav" aria-label="Menu categories">
      <div className="m-catnav-inner">
        <div className="m-chips" ref={scrollerRef}>
          {categories.map((category) => {
            const active = category.id === activeCategory;
            return (
              <button
                key={category.id}
                type="button"
                data-category={category.id}
                className={`m-chip ${active ? "is-active" : ""}`}
                aria-pressed={active}
                onClick={() => onSelect(category.id)}
              >
                {active ? (
                  <motion.span
                    layoutId="m-category-pill"
                    className="m-chip-pill"
                    aria-hidden="true"
                    transition={
                      motionPrefs.reduced
                        ? { duration: 0 }
                        : { type: "spring", stiffness: 420, damping: 36, mass: 0.7 }
                    }
                  />
                ) : null}
                <span className="m-chip-label">{category.name}</span>
              </button>
            );
          })}
        </div>
        <span className="m-catnav-count" aria-hidden="true">
          {categories.length} sections
        </span>
      </div>
    </nav>
  );
}
