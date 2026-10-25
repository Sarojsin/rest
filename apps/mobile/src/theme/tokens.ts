/**
 * Design tokens for the staff app.
 *
 * Mirrored from the website's `apps/web/src/styles/tokens.css` and its two
 * staff themes (`themes/management.css`, `themes/operations.css`). React Native
 * cannot consume CSS custom properties, so these values are kept in sync by
 * hand — treat the CSS as the source of truth when the palette changes.
 */

export type ThemeName = "management" | "operations";

export type ThemeColors = {
  bg: string;
  surface: string;
  surface2: string;
  surface3: string;
  ink: string;
  muted: string;
  line: string;
  lineStrong: string;
  primary: string;
  primaryHover: string;
  onPrimary: string;
  primarySoft: string;
  success: string;
  successSoft: string;
  warn: string;
  warnSoft: string;
  danger: string;
  dangerSoft: string;
  info: string;
  infoSoft: string;
  navBg: string;
  navInk: string;
  navMuted: string;
};

export type Theme = {
  name: ThemeName;
  color: ThemeColors;
};

export const space = {
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  7: 32,
  8: 40,
  9: 48,
} as const;

export const radius = {
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
  pill: 999,
} as const;

export const text = {
  xs: 12,
  sm: 13.5,
  base: 15,
  md: 17,
  lg: 21,
  xl: 26,
  "2xl": 30,
} as const;

/** Minimum comfortable touch target. */
export const tap = 48;

const management: Theme = {
  name: "management",
  color: {
    bg: "#f4f6f9",
    surface: "#ffffff",
    surface2: "#f8fafc",
    surface3: "#eef2f7",
    ink: "#1f2937",
    muted: "#64748b",
    line: "#e2e8f0",
    lineStrong: "#cbd5e1",
    primary: "#2563eb",
    primaryHover: "#1d4ed8",
    onPrimary: "#ffffff",
    primarySoft: "#eef4ff",
    success: "#047857",
    successSoft: "#e7f5ef",
    warn: "#b45309",
    warnSoft: "#fdf3e3",
    danger: "#b91c1c",
    dangerSoft: "#fcecec",
    info: "#1d4ed8",
    infoSoft: "#eef4ff",
    navBg: "#0f1b2d",
    navInk: "#eef3fa",
    navMuted: "#94a7c1",
  },
};

const operations: Theme = {
  name: "operations",
  color: {
    bg: "#f6f7f6",
    surface: "#ffffff",
    surface2: "#f0f2f1",
    surface3: "#e4e7e5",
    ink: "#111827",
    muted: "#4b5563",
    line: "#d6dad7",
    lineStrong: "#aeb5b0",
    primary: "#15803d",
    primaryHover: "#166534",
    onPrimary: "#ffffff",
    primarySoft: "#e6f3ea",
    success: "#15803d",
    successSoft: "#e6f3ea",
    warn: "#b45309",
    warnSoft: "#fdf1e0",
    danger: "#b91c1c",
    dangerSoft: "#fdecec",
    info: "#1e40af",
    infoSoft: "#e8eefc",
    navBg: "#14181a",
    navInk: "#f8fafc",
    navMuted: "#a7b0b5",
  },
};

export const themes = { management, operations } as const;

/**
 * Floor staff read the management palette; kitchen and cashier stations use the
 * high-contrast operations palette, matching the web split.
 */
export function themeForPermissions(permissions: string[]): Theme {
  if (permissions.includes("orders.create")) return management;
  return operations;
}

export function themeForRole(role: string): Theme {
  if (role === "kitchen" || role === "cashier") return operations;
  return management;
}
