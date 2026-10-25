import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { MenuCategory, Order, ServiceCall } from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { tableKeys } from "@/features/tables/api";

export const orderKeys = {
  list: (restaurantId: string, status: string) => ["orders", restaurantId, status] as const,
  detail: (restaurantId: string, id: string) => ["order", restaurantId, id] as const,
  calls: (restaurantId: string, status: string) => ["service-calls", restaurantId, status] as const,
  menu: (restaurantId: string) => ["menu", restaurantId] as const,
};

function useRestaurantId(): string {
  const { me } = useAuth();
  return me?.membership.restaurant_id ?? "anonymous";
}

export function useOrders(status: string, options?: { enabled?: boolean; refetchInterval?: number }) {
  const { me } = useAuth();
  const restaurantId = useRestaurantId();
  return useQuery({
    queryKey: orderKeys.list(restaurantId, status),
    queryFn: () => api<Order[]>(`/api/v1/orders?status=${encodeURIComponent(status)}`),
    enabled: Boolean(me) && (options?.enabled ?? true),
    refetchInterval: options?.refetchInterval ?? 10_000,
  });
}

export function useOrder(orderId: string | undefined) {
  const { me } = useAuth();
  const restaurantId = useRestaurantId();
  return useQuery({
    queryKey: orderKeys.detail(restaurantId, orderId ?? "none"),
    queryFn: () => api<Order>(`/api/v1/orders/${orderId}`),
    enabled: Boolean(me && orderId),
  });
}

export function useServiceCalls(status = "REQUESTED") {
  const { me } = useAuth();
  const restaurantId = useRestaurantId();
  return useQuery({
    queryKey: orderKeys.calls(restaurantId, status),
    queryFn: () => api<ServiceCall[]>(`/api/v1/service-calls?status=${encodeURIComponent(status)}`),
    enabled: Boolean(me),
    refetchInterval: 10_000,
  });
}

export function useMenu() {
  const { me } = useAuth();
  const restaurantId = useRestaurantId();
  return useQuery({
    queryKey: orderKeys.menu(restaurantId),
    queryFn: () => api<MenuCategory[]>("/api/v1/menu"),
    enabled: Boolean(me),
    // The menu changes rarely; refetching it every ten seconds wastes the
    // kitchen tablet's battery for no benefit.
    staleTime: 60_000,
  });
}

/** QR orders and waiter orders land in the same kitchen queue. */
function useInvalidateFloor() {
  const queryClient = useQueryClient();
  const restaurantId = useRestaurantId();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["orders", restaurantId] });
    void queryClient.invalidateQueries({ queryKey: tableKeys.all(restaurantId) });
    void queryClient.invalidateQueries({ queryKey: ["service-calls", restaurantId] });
  };
}

export function useAcceptOrder() {
  const invalidate = useInvalidateFloor();
  return useMutation({
    mutationFn: (orderId: string) =>
      api<Order>(`/api/v1/orders/${orderId}/accept`, { method: "POST" }),
    onSuccess: invalidate,
  });
}

export function useRejectOrder() {
  const invalidate = useInvalidateFloor();
  return useMutation({
    mutationFn: (input: { orderId: string; reasonCode: string; note: string }) =>
      api<Order>(`/api/v1/orders/${input.orderId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason_code: input.reasonCode, note: input.note }),
      }),
    onSuccess: invalidate,
  });
}

export function useAcknowledgeCall() {
  const invalidate = useInvalidateFloor();
  return useMutation({
    mutationFn: (callId: string) =>
      api<ServiceCall>(`/api/v1/service-calls/${callId}/acknowledge`, { method: "POST" }),
    onSuccess: invalidate,
  });
}

export type DraftLine = {
  menuItemId: string;
  quantity: number;
  specialInstructions: string;
};

/**
 * `idempotencyKey` is supplied by the caller and must stay the same across
 * retries of the same draft. Generating a new key per attempt would let a
 * timed-out request create a second order.
 */
export function useCreateOrder() {
  const invalidate = useInvalidateFloor();
  return useMutation({
    mutationFn: (input: {
      tableId: string;
      items: DraftLine[];
      customerNote: string;
      idempotencyKey: string;
    }) =>
      api<Order>("/api/v1/orders", {
        method: "POST",
        idempotencyKey: input.idempotencyKey,
        body: JSON.stringify({
          table_id: input.tableId,
          items: input.items.map((line) => ({
            menu_item_id: line.menuItemId,
            quantity: line.quantity,
            special_instructions: line.specialInstructions,
          })),
          customer_note: input.customerNote,
        }),
      }),
    onSuccess: invalidate,
  });
}
