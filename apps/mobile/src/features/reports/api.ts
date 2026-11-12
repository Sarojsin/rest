import { useQuery } from "@tanstack/react-query";

import type {
  SalesReport,
  AuditEvent,
} from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const reportKeys = {
  sales: (restaurantId: string) => ["reports", "sales", restaurantId] as const,
  advanced: (restaurantId: string, days: number) => ["reports", "advanced", restaurantId, days] as const,
  payments: (restaurantId: string, days: number) => ["reports", "payments", restaurantId, days] as const,
  kitchenSpeed: (restaurantId: string, days: number) => ["reports", "kitchen-speed", restaurantId, days] as const,
  auditEvents: (restaurantId: string) => ["reports", "audit-events", restaurantId] as const,
};

function useRestaurantContext() {
  const { getRestaurantId } = useAuth();
  return {
    restaurantId: getRestaurantId(),
  };
}

export function useSalesReport() {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: reportKeys.sales(restaurantId ?? ""),
    queryFn: () => api<SalesReport>("/api/v1/reports/sales"),
    enabled: Boolean(me && restaurantId),
    staleTime: 60_000,
  });
}

export function useAdvancedReport(days = 30) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: reportKeys.advanced(restaurantId ?? "", days),
    queryFn: () => api<{
      window_days: number;
      currency_code: string;
      sales: SalesReport;
      average_order_minor: number;
      daily: Array<{ date: string; order_count: number; gross_sales_minor: number }>;
    }>(`/api/v1/reports/advanced?days=${days}`),
    enabled: Boolean(me && restaurantId),
  });
}

export function usePaymentsReport(days = 30) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: reportKeys.payments(restaurantId ?? "", days),
    queryFn: () => api<{
      window_days: number;
      currency_code: string;
      total_collected_minor: number;
      succeeded_count: number;
      failed_count: number;
      methods: Array<{ method: string; payment_count: number; amount_minor: number }>;
    }>(`/api/v1/reports/payments?days=${days}`),
    enabled: Boolean(me && restaurantId),
  });
}

export function useKitchenSpeedReport(days = 30) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: reportKeys.kitchenSpeed(restaurantId ?? "", days),
    queryFn: () => api<{
      window_days: number;
      completed_ticket_count: number;
      avg_prep_seconds: number;
      fastest_prep_seconds: number;
      slowest_prep_seconds: number;
      slowest_tickets: Array<{
        ticket_id: string;
        ticket_number: number;
        status: string;
        started_at: string | null;
        ready_at: string;
        prep_seconds: number;
      }>;
    }>(`/api/v1/reports/kitchen-speed?days=${days}`),
    enabled: Boolean(me && restaurantId),
  });
}

export function useAuditEvents() {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: reportKeys.auditEvents(restaurantId ?? ""),
    queryFn: () => api<AuditEvent[]>("/api/v1/audit-events"),
    enabled: Boolean(me && restaurantId),
    staleTime: 30_000,
  });
}