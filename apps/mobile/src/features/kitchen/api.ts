import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { KitchenTicket, ServiceCall } from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const kitchenKeys = {
  tickets: (restaurantId: string, branchId: string | null) => ["kitchen-tickets", restaurantId, branchId] as const,
  serviceCalls: (restaurantId: string, branchId: string | null) => ["service-calls", restaurantId, branchId] as const,
};

function useRestaurantContext() {
  const { getRestaurantId, getBranchId } = useAuth();
  return {
    restaurantId: getRestaurantId(),
    branchId: getBranchId(),
  };
}

export function useTickets() {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: kitchenKeys.tickets(restaurantId ?? "", branchId),
    queryFn: () => {
      const params = new URLSearchParams();
      if (branchId) params.set("branch_id", branchId);
      const query = params.toString();
      return api<KitchenTicket[]>(`/api/v1/kitchen/tickets${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId),
    refetchInterval: 4_000,
  });
}

export function useServiceCalls(status: string = "REQUESTED") {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: [...kitchenKeys.serviceCalls(restaurantId ?? "", branchId), status],
    queryFn: () => {
      const params = new URLSearchParams({ status });
      if (branchId) params.set("branch_id", branchId);
      return api<ServiceCall[]>(`/api/v1/service-calls?${params.toString()}`);
    },
    enabled: Boolean(me && restaurantId),
    refetchInterval: 5_000,
  });
}

export function useAcknowledgeServiceCall() {
  const queryClient = useQueryClient();
  const { restaurantId, branchId } = useRestaurantContext();
  return useMutation({
    mutationFn: (callId: string) =>
      api<ServiceCall>(`/api/v1/service-calls/${callId}/acknowledge`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: kitchenKeys.serviceCalls(restaurantId ?? "", branchId) });
    },
  });
}

export function useSetItemStatus() {
  const queryClient = useQueryClient();
  const { restaurantId, branchId } = useRestaurantContext();
  return useMutation({
    mutationFn: (input: { itemId: string; status: "PREPARING" | "READY" }) =>
      api<KitchenTicket>(`/api/v1/kitchen/ticket-items/${input.itemId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: input.status }),
      }),
    onSuccess: (ticket) => {
      queryClient.setQueryData<KitchenTicket[]>(
        kitchenKeys.tickets(restaurantId ?? "", branchId),
        (previous) =>
          previous ? previous.map((row) => (row.id === ticket.id ? ticket : row)) : previous
      );
      void queryClient.invalidateQueries({ queryKey: ["service-calls", restaurantId, branchId] });
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
  const { restaurantId, branchId } = useRestaurantContext();
  return useMutation({
    mutationFn: (itemId: string) =>
      api<KitchenTicket>(`/api/v1/kitchen/ticket-items/${itemId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: "SERVED" }),
      }),
    onSuccess: (ticket) => {
      queryClient.setQueryData<KitchenTicket[]>(
        kitchenKeys.tickets(restaurantId ?? "", branchId),
        (previous) =>
          previous ? previous.map((row) => (row.id === ticket.id ? ticket : row)) : previous
      );
      void queryClient.invalidateQueries({ queryKey: ["service-calls", restaurantId, branchId] });
      void queryClient.invalidateQueries({ queryKey: ["orders", restaurantId, branchId] });
    },
  });
}

export function useCallWaiter() {
  const queryClient = useQueryClient();
  const { restaurantId, branchId } = useRestaurantContext();
  return useMutation({
    mutationFn: (ticketId: string) =>
      api<KitchenTicket>(`/api/v1/kitchen/tickets/${ticketId}/call-waiter`, { method: "POST" }),
    onSuccess: (ticket) => {
      queryClient.setQueryData<KitchenTicket[]>(
        kitchenKeys.tickets(restaurantId ?? "", branchId),
        (previous) =>
          previous ? previous.map((row) => (row.id === ticket.id ? ticket : row)) : previous
      );
      void queryClient.invalidateQueries({ queryKey: ["service-calls", restaurantId, branchId] });
    },
  });
}