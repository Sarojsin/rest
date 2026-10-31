/**
 * Public brand text for the pages that render without a restaurant context
 * (landing page, login screen). Tenant-aware screens show
 * `restaurant_name` from the API instead — never hardcode it in components.
 *
 * Set `VITE_BRAND_NAME` in `.env` / the hosting platform when deploying for a
 * specific restaurant. A brand name is not a secret, so a VITE_ variable is
 * safe to compile into the client bundle.
 */
export const BRAND_NAME = (import.meta.env.VITE_BRAND_NAME as string | undefined)?.trim() || "Restaurant Table";

/** Monogram for the square logo mark ("Restaurant Table" → "RT"). */
export const BRAND_MARK = monogram(BRAND_NAME);

/**
 * Initials of any restaurant name for the logo mark. Used by tenant-aware
 * screens where the name is server-provided.
 */
export function monogram(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase() ?? "")
      .join("") || "RT"
  );
}
