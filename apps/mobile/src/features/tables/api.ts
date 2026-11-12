import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { Table } from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Query keys are tenant-scoped so a membership change can never reuse data. */
export const tableKeys = {
  all: (restaurantId: string, branchId: string | null) => ["tables", restaurantId, branchId] as const,
};

function useRestaurantContext() {
  const { getRestaurantId, getBranchId } = useAuth();
  return {
    restaurantId: getRestaurantId(),
    branchId: getBranchId(),
  };
}

export function useTables(options?: { refetchInterval?: number }) {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: tableKeys.all(restaurantId ?? "", branchId),
    queryFn: () => {
      const params = new URLSearchParams();
      if (branchId) params.set("branch_id", branchId);
      const query = params.toString();
      return api<Table[]>(`/api/v1/tables${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId),
    refetchInterval: options?.refetchInterval ?? 15_000,
  });
}

/**
 * Order payloads carry `table_id` only. Resolve display names from the shared
 * table cache instead of inventing a second source of truth.
 */
export function useTableNames(): (tableId: string) => string {
  const tables = useTables({ refetchInterval: 60_000 });
  return useMemo(() => {
    const names = new Map<string, string>();
    for (const table of tables.data ?? []) names.set(table.id, table.display_name);
    return (tableId: string) => names.get(tableId) ?? "Table";
  }, [tables.data]);
}

export function useTable(tableId: string | undefined): Table | undefined {
  const tables = useTables({ refetchInterval: 15_000 });
  return tables.data?.find((table) => table.id === tableId);
}
