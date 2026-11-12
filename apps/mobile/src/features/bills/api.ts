import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Bill, PaymentMethodConfig } from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const billKeys = {
  bySession: (restaurantId: string, branchId: string | null, sessionId: string) =>
    ["bill", restaurantId, branchId, sessionId] as const,
  methods: (restaurantId: string) => ["payment-methods", restaurantId] as const,
};

function useRestaurantContext() {
  const { getRestaurantId, getBranchId } = useAuth();
  return {
    restaurantId: getRestaurantId(),
    branchId: getBranchId(),
  };
}

function isNotFound(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    (error as { status?: number }).status === 404
  );
}

/**
 * Returns `null` when no bill has been issued for the session yet — the API
 * answers 404 and that is a normal state, not an error to shout about.
 */
export function useBill(sessionId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: billKeys.bySession(restaurantId ?? "", branchId, sessionId ?? "none"),
    queryFn: async () => {
      try {
        return await api<Bill>(`/api/v1/sessions/${sessionId}/bill`);
      } catch (error) {
        if (isNotFound(error)) return null;
        throw error;
      }
    },
    enabled: Boolean(me && sessionId && restaurantId),
    refetchInterval: 10_000,
  });
}

export function usePaymentMethods() {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: billKeys.methods(restaurantId ?? ""),
    queryFn: () => api<PaymentMethodConfig[]>("/api/v1/payment-methods"),
    enabled: Boolean(me && restaurantId),
    staleTime: 60_000,
  });
}

export function useIssueBill() {
  const queryClient = useQueryClient();
  const { restaurantId, branchId } = useRestaurantContext();
  return useMutation({
    mutationFn: (sessionId: string) =>
      api<Bill>(`/api/v1/sessions/${sessionId}/bill/issue`, { method: "POST" }),
    onSuccess: (bill) => {
      queryClient.setQueryData(billKeys.bySession(restaurantId ?? "", branchId, bill.dining_session_id), bill);
      void queryClient.invalidateQueries({ queryKey: ["tables", restaurantId, branchId] });
    },
  });
}

/**
 * `idempotencyKey` must be reused if the cashier retries the same tender after a
 * timeout. The caller owns it so the key survives a re-render.
 */
export function useRecordPayment() {
  const queryClient = useQueryClient();
  const { restaurantId, branchId } = useRestaurantContext();
  return useMutation({
    mutationFn: (input: {
      billId: string;
      sessionId: string;
      methodId: string;
      amountMinor: number;
      note: string;
      idempotencyKey: string;
    }) =>
      api<Bill>(`/api/v1/bills/${input.billId}/payments`, {
        method: "POST",
        idempotencyKey: input.idempotencyKey,
        body: JSON.stringify({
          method_id: input.methodId,
          amount_minor: input.amountMinor,
          note: input.note,
        }),
      }),
    onSuccess: (bill, input) => {
      queryClient.setQueryData(billKeys.bySession(restaurantId ?? "", branchId, input.sessionId), bill);
      void queryClient.invalidateQueries({ queryKey: ["tables", restaurantId, branchId] });
    },
  });
}

// P2.7: Payment methods management
export function useCreatePaymentMethod() {
  const queryClient = useQueryClient();
  const { restaurantId } = useRestaurantContext();
  return useMutation({
    mutationFn: (input: {
      label: string;
      kind: "CASH" | "QR";
      accountHint: string;
      instructions: string;
      displayOrder: number;
      qrImage?: string; // base64
    }) =>
      api<PaymentMethodConfig>("/api/v1/payment-methods", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: billKeys.methods(restaurantId ?? "") });
    },
  });
}

export function useUpdatePaymentMethod() {
  const queryClient = useQueryClient();
  const { restaurantId } = useRestaurantContext();
  return useMutation({
    mutationFn: (input: {
      id: string;
      label?: string;
      accountHint?: string;
      instructions?: string;
      displayOrder?: number;
      isActive?: boolean;
      qrImage?: string;
    }) =>
      api<PaymentMethodConfig>(`/api/v1/payment-methods/${input.id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: billKeys.methods(restaurantId ?? "") });
    },
  });
}

export function useDeletePaymentMethod() {
  const queryClient = useQueryClient();
  const { restaurantId } = useRestaurantContext();
  return useMutation({
    mutationFn: (id: string) =>
      api<void>(`/api/v1/payment-methods/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: billKeys.methods(restaurantId ?? "") });
    },
  });
}
