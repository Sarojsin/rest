import type { Theme } from "../theme/tokens";

/**
 * Mirrors `apps/web/src/components/StatusBadge.tsx`.
 *
 * The label is what communicates state; the tone only decorates it. Kitchen and
 * cashier screens must stay readable for staff who cannot distinguish the
 * colour pairings, so never render a tone without its text.
 */
const LABELS: Record<string, string> = {
  PENDING_CONFIRMATION: "Awaiting confirmation",
  ACCEPTED: "Confirmed",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
  COMPLETED: "Served",
  NEW: "New",
  IN_PROGRESS: "Cooking",
  PREPARING: "Cooking",
  READY: "Ready",
  SERVED: "Served",
  PUBLISHED: "Published",
  UNAVAILABLE: "Unavailable",
  DRAFT: "Draft",
  ARCHIVED: "Archived",
  AVAILABLE: "Available",
  OCCUPIED: "Occupied",
  CHECKOUT: "Checkout",
  OPEN: "Open",
  ISSUED: "Issued",
  PARTIALLY_PAID: "Part paid",
  PAID: "Paid",
  VOID: "Void",
  REQUESTED: "Requested",
  ACKNOWLEDGED: "Acknowledged",
};

export type Tone =
  | "pending"
  | "info"
  | "accepted"
  | "ready"
  | "published"
  | "available"
  | "paid"
  | "served"
  | "rejected"
  | "cancelled"
  | "unavailable"
  | "void"
  | "draft"
  | "archived";

const TONES: Record<string, Tone> = {
  PENDING_CONFIRMATION: "pending",
  REQUESTED: "pending",
  ISSUED: "pending",
  PARTIALLY_PAID: "pending",
  IN_PROGRESS: "pending",
  PREPARING: "pending",
  CHECKOUT: "pending",
  OCCUPIED: "pending",
  NEW: "info",
  OPEN: "info",
  SERVED: "info",
  ACKNOWLEDGED: "info",
  ACCEPTED: "accepted",
  READY: "ready",
  PUBLISHED: "published",
  AVAILABLE: "available",
  PAID: "paid",
  COMPLETED: "served",
  REJECTED: "rejected",
  CANCELLED: "cancelled",
  UNAVAILABLE: "unavailable",
  VOID: "void",
  DRAFT: "draft",
  ARCHIVED: "archived",
};

export function formatStatus(status: string): string {
  return (
    LABELS[status] ??
    status
      .toLowerCase()
      .replace(/_/g, " ")
      .replace(/^\w/, (char) => char.toUpperCase())
  );
}

export function toneFor(status: string): Tone {
  return TONES[status] ?? "info";
}

export type ToneColors = { fg: string; bg: string };

export function toneColors(theme: Theme, tone: Tone): ToneColors {
  const c = theme.color;
  switch (tone) {
    case "pending":
      return { fg: c.warn, bg: c.warnSoft };
    case "accepted":
    case "ready":
    case "published":
    case "available":
    case "paid":
      return { fg: c.success, bg: c.successSoft };
    case "rejected":
    case "cancelled":
    case "void":
      return { fg: c.danger, bg: c.dangerSoft };
    case "unavailable":
    case "draft":
    case "archived":
      return { fg: c.muted, bg: c.surface3 };
    case "served":
    case "info":
    default:
      return { fg: c.info, bg: c.infoSoft };
  }
}

export function statusColors(theme: Theme, status: string): ToneColors {
  return toneColors(theme, toneFor(status));
}
