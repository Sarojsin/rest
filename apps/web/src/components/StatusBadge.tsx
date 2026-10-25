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

/**
 * Colour tone per server status. The tone only ever decorates the badge — the
 * text label is what actually communicates the state.
 */
const TONES: Record<string, string> = {
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

/**
 * Status is never communicated by colour alone: the badge always carries a
 * human-readable label, and the tone class only supplies the colour pairing.
 */
export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const tone = TONES[status] ?? "info";
  return <span className={`badge ${tone}`}>{label ?? formatStatus(status)}</span>;
}
