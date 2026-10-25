import { formatMoney } from "@rest/api-client";

export { formatMoney };

/** Milliseconds after which an open ticket is worth flagging to the kitchen. */
export const LATE_AFTER_MS = 12 * 60_000;

/** "14:32" in the device's locale, for ticket and bill timestamps. */
export function formatClock(iso: string | null | undefined): string {
  if (!iso) return "—";
  const value = Date.parse(iso);
  if (Number.isNaN(value)) return "—";
  return new Date(value).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * How long something has been waiting. Used for kitchen ticket age and pending
 * QR orders, so the wording stays in one place.
 */
export function elapsed(iso: string | null | undefined, now: number): string {
  if (!iso) return "—";
  const started = Date.parse(iso);
  if (Number.isNaN(started)) return "—";
  const minutes = Math.floor(Math.max(0, now - started) / 60_000);
  if (minutes < 1) return "<1 min";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours} h ${minutes % 60} min`;
}

export function isLate(iso: string | null | undefined, now: number): boolean {
  if (!iso) return false;
  const started = Date.parse(iso);
  return !Number.isNaN(started) && now - started > LATE_AFTER_MS;
}

/** Sum of quantities, ignoring cancelled lines. */
export function activeItemCount(
  items: { quantity_snapshot?: number; quantity?: number; status: string }[]
): number {
  return items
    .filter((item) => item.status !== "CANCELLED")
    .reduce((total, item) => total + (item.quantity_snapshot ?? item.quantity ?? 0), 0);
}
