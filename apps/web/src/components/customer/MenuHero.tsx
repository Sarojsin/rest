import { motion } from "framer-motion";

import type { MenuItem, PublicMenu } from "../../lib/api";
import { formatMoney } from "../../lib/api";
import { EASE_OUT, fadeUp, useMenuMotion } from "../../lib/motion";

/**
 * Editorial hero for the table-side menu. The cover photo is a decorative
 * asset shipped with the site; every restaurant fact (name, table, status,
 * prices) comes from the public menu API.
 */
const HERO_IMAGE = "/menu/food/jhol-momo.jpg";

type MenuHeroProps = {
  menu: PublicMenu;
  search: string;
  onSearchChange: (value: string) => void;
  onClearSearch: () => void;
  featured: MenuItem | null;
  onOpenFeatured: (item: MenuItem) => void;
};

export function MenuHero({
  menu,
  search,
  onSearchChange,
  onClearSearch,
  featured,
  onOpenFeatured,
}: MenuHeroProps) {
  const motionPrefs = useMenuMotion();
  const dishCount = menu.categories.reduce((total, category) => total + category.items.length, 0);
  const paused = !menu.qr_ordering_enabled;

  return (
    <section className="m-hero" aria-labelledby="menu-restaurant-name">
      <div className="m-hero-media" aria-hidden="true">
        <motion.img
          src={HERO_IMAGE}
          alt=""
          initial={motionPrefs.reduced ? false : { scale: 1.06 }}
          animate={{ scale: 1 }}
          transition={motionPrefs.reduced ? motionPrefs.none : { duration: 1.1, ease: EASE_OUT }}
        />
      </div>

      <motion.div
        className="m-hero-inner"
        variants={motionPrefs.hero}
        initial={motionPrefs.reduced ? false : "hidden"}
        animate="show"
      >
        <div className="m-hero-copy">
          <motion.div className="m-hero-eyebrow" variants={fadeUp}>
            <span className={`m-pill ${paused ? "is-paused" : ""}`}>
              <span className="m-pill-dot" aria-hidden="true" />
              {paused ? "Ordering paused" : "Taking orders"}
            </span>
            <span className="m-pill">{menu.table_display_name}</span>
          </motion.div>

          <motion.h1 id="menu-restaurant-name" className="m-hero-title" variants={fadeUp}>
            {menu.restaurant_name}
          </motion.h1>

          <motion.p className="m-hero-sub" variants={fadeUp}>
            {paused
              ? "The kitchen has paused new table orders. Please ask a member of staff to take your order."
              : "Browse the kitchen's current menu, build your order at your own pace, and send it to the floor. A team member confirms every request before cooking starts."}
          </motion.p>

          <motion.ul className="m-hero-meta" variants={fadeUp}>
            <li>
              <DishIcon />
              {dishCount} {dishCount === 1 ? "dish" : "dishes"} on the menu
            </li>
            <li>
              <CheckIcon />
              Staff-confirmed orders
            </li>
            <li>
              <RefreshIcon />
              Live prices &amp; availability
            </li>
          </motion.ul>

          <motion.div className="m-hero-search" variants={fadeUp}>
            <div className="m-search-field">
              <span className="m-search-icon" aria-hidden="true">
                <SearchIcon />
              </span>
              <label className="visually-hidden" htmlFor="menu-search-input">
                Search dishes or ingredients
              </label>
              <input
                id="menu-search-input"
                className="m-search-input"
                type="search"
                value={search}
                onChange={(event) => onSearchChange(event.target.value)}
                placeholder="Search dishes or ingredients"
                autoComplete="off"
                enterKeyHint="search"
              />
              {search ? (
                <button
                  type="button"
                  className="m-search-clear"
                  onClick={onClearSearch}
                  aria-label="Clear search"
                >
                  <CloseIcon />
                </button>
              ) : null}
            </div>
          </motion.div>
        </div>

        {featured ? (
          <motion.div className="m-hero-aside" variants={fadeUp}>
            <button
              type="button"
              className="m-featured"
              onClick={() => onOpenFeatured(featured)}
              aria-label={`View ${featured.name} — ${formatMoney(
                featured.current_price_minor,
                featured.currency_code
              )}`}
            >
              <span className="m-featured-media" aria-hidden="true">
                {featured.image_path ? (
                  <img src={featured.image_path} alt="" loading="lazy" decoding="async" />
                ) : (
                  featured.image_emoji || featured.name.slice(0, 1)
                )}
              </span>
              <span className="m-featured-body">
                <span className="m-featured-label">Featured dish</span>
                <span className="m-featured-name">{featured.name}</span>
                <span className="m-featured-price">
                  {formatMoney(featured.current_price_minor, featured.currency_code)}
                </span>
              </span>
            </button>
          </motion.div>
        ) : null}
      </motion.div>
    </section>
  );
}

/* The cart storage key helper stays in the page so the hero remains
   presentational. */

function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
      <path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M20 12a8 8 0 1 1-2.6-5.9M20 4.5V10h-5.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DishIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 15h16M6 15a6 6 0 0 1 12 0" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M3 19h18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M20 6 9 17l-5-5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
