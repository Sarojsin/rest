/**
 * One-click demo sign-ins for showing the product to restaurant owners with
 * the seeded sample data. This is a sales/demo feature — for a real
 * deployment set `VITE_DEMO_ACCOUNTS=0` and both the home-page demo strip and
 * the login quick-fill chips disappear. The standalone build flag is public
 * (not a secret) and safe to compile into the client bundle.
 */
export const DEMO_ACCOUNTS = [
  { role: "Owner", email: "owner@harbor.example", password: "HarborOwner!1" },
  { role: "Manager", email: "manager@harbor.example", password: "HarborManager!1" },
  { role: "Waiter", email: "waiter@harbor.example", password: "HarborWaiter!1" },
  { role: "Kitchen", email: "kitchen@harbor.example", password: "HarborKitchen!1" },
  { role: "Cashier", email: "cashier@harbor.example", password: "HarborCashier!1" },
] as const;

/** Role shown when a restaurant owner clicks a demo chip on the home page. */
export const DEMO_HINT: Record<string, string> = {
  Owner: "menus, tables, staff, reports",
  Manager: "everything the owner can do",
  Waiter: "the floor: tables and QR orders",
  Kitchen: "the kitchen board",
  Cashier: "bills and payments",
};

export const DEMO_ENABLED = import.meta.env.VITE_DEMO_ACCOUNTS !== "0";

/** Login URL that prefills the credentials (the login form reads these params). */
export function demoLoginHref(account: (typeof DEMO_ACCOUNTS)[number]): string {
  return `/login?email=${encodeURIComponent(account.email)}&password=${encodeURIComponent(
    account.password
  )}`;
}
