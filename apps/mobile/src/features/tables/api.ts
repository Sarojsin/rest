import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { Table } from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Query keys are tenant-scoped so a membership change can never reuse data. */
export const tableKeys = {
  all: (restaurantId: string) => ["tables", restaurantId] as const,
};

export function useTables(options?: { refetchInterval?: number }) {
  const { me } = useAuth();
  const restaurantId = me?.membership.restaurant_id ?? "anonymous";
  return useQuery({
    queryKey: tableKeys.all(restaurantId),
    queryFn: () => api<Table[]>("/api/v1/tables"),
    enabled: Boolean(me),
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
