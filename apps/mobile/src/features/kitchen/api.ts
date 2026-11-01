import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { KitchenTicket, ServiceCall } from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const kitchenKeys = {
  tickets: (restaurantId: string) => ["kitchen-tickets", restaurantId] as const,
  serviceCalls: (restaurantId: string) => ["service-calls", restaurantId] as const,
};

function useRestaurantId(): string {
  const { me } = useAuth();
  return me?.membership.restaurant_id ?? "anonymous";
}

export function useTickets() {
  const { me } = useAuth();
  const restaurantId = useRestaurantId();
  return useQuery({
    queryKey: kitchenKeys.tickets(restaurantId),
    queryFn: () => api<KitchenTicket[]>("/api/v1/kitchen/tickets"),
    enabled: Boolean(me),
    // The board is the one screen where four seconds of staleness matters.
    refetchInterval: 4_000,
  });
}

export function useServiceCalls(status: string = "REQUESTED") {
  const { me } = useAuth();
  const restaurantId = useRestaurantId();
  return useQuery({
    queryKey: [...kitchenKeys.serviceCalls(restaurantId), status],
    queryFn: () => api<ServiceCall[]>(`/api/v1/service-calls?status=${status}`),
    enabled: Boolean(me),
    refetchInterval: 5_000,
  });
}

export function useAcknowledgeServiceCall() {
  const queryClient = useQueryClient();
  const restaurantId = useRestaurantId();
  return useMutation({
    mutationFn: (callId: string) =>
      api<ServiceCall>(`/api/v1/service-calls/${callId}/acknowledge`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: kitchenKeys.serviceCalls(restaurantId) });
    },
  });
}

export function useSetItemStatus() {
  const queryClient = useQueryClient();
  const restaurantId = useRestaurantId();
  return useMutation({
    mutationFn: (input: { itemId: string; status: "PREPARING" | "READY" }) =>
      api<KitchenTicket>(`/api/v1/kitchen/ticket-items/${input.itemId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: input.status }),
      }),
    onSuccess: (ticket) => {
      // The response is the authoritative ticket; replace it in place so the
      // board does not wait for the next poll.
      queryClient.setQueryData<KitchenTicket[]>(
        kitchenKeys.tickets(restaurantId),
        (previous) =>
          previous ? previous.map((row) => (row.id === ticket.id ? ticket : row)) : previous
      );
      void queryClient.invalidateQueries({ queryKey: ["service-calls", restaurantId] });
    },
  });
}

/**
 * Waiter action: hand a ready kitchen item to the guest (`SERVED` requires
 * `orders.serve`, which the kitchen role lacks). Serving the last item also
 * completes the order, so the waiter's order list is refreshed too.
 */
export function useServeItem() {
  const queryClient = useQueryClient();
  const restaurantId = useRestaurantId();
  return useMutation({
    mutationFn: (itemId: string) =>
      api<KitchenTicket>(`/api/v1/kitchen/ticket-items/${itemId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: "SERVED" }),
      }),
    onSuccess: (ticket) => {
      queryClient.setQueryData<KitchenTicket[]>(
        kitchenKeys.tickets(restaurantId),
        (previous) =>
          previous ? previous.map((row) => (row.id === ticket.id ? ticket : row)) : previous
      );
      void queryClient.invalidateQueries({ queryKey: ["service-calls", restaurantId] });
      void queryClient.invalidateQueries({ queryKey: ["orders", restaurantId] });
    },
  });
}

export function useCallWaiter() {
  const queryClient = useQueryClient();
  const restaurantId = useRestaurantId();
  return useMutation({
    mutationFn: (ticketId: string) =>
      api<KitchenTicket>(`/api/v1/kitchen/tickets/${ticketId}/call-waiter`, { method: "POST" }),
    onSuccess: (ticket) => {
      queryClient.setQueryData<KitchenTicket[]>(
        kitchenKeys.tickets(restaurantId),
        (previous) =>
          previous ? previous.map((row) => (row.id === ticket.id ? ticket : row)) : previous
      );
      void queryClient.invalidateQueries({ queryKey: ["service-calls", restaurantId] });
    },
  });
}