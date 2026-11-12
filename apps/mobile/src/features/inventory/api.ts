import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  Ingredient,
  Supplier,
  PurchaseOrder,
  StockMovement,
  IngredientBatch,
  StockCount,
  LowStockReport,
  ConsumptionReport,
  RecipeIngredient,
} from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const inventoryKeys = {
  ingredients: (restaurantId: string, branchId: string | null, status?: string) =>
    ["ingredients", restaurantId, branchId, status] as const,
  ingredient: (restaurantId: string, id: string) =>
    ["ingredient", restaurantId, id] as const,
  suppliers: (restaurantId: string, activeOnly?: boolean) =>
    ["suppliers", restaurantId, activeOnly] as const,
  supplier: (restaurantId: string, id: string) =>
    ["supplier", restaurantId, id] as const,
  purchaseOrders: (restaurantId: string, branchId: string | null, status?: string) =>
    ["purchase-orders", restaurantId, branchId, status] as const,
  purchaseOrder: (restaurantId: string, id: string) =>
    ["purchase-order", restaurantId, id] as const,
  stockMovements: (restaurantId: string, branchId: string | null, ingredientId?: string) =>
    ["stock-movements", restaurantId, branchId, ingredientId] as const,
  batches: (restaurantId: string, branchId: string | null, ingredientId?: string) =>
    ["batches", restaurantId, branchId, ingredientId] as const,
  batch: (restaurantId: string, id: string) =>
    ["batch", restaurantId, id] as const,
  stockCounts: (restaurantId: string, branchId: string | null, status?: string) =>
    ["stock-counts", restaurantId, branchId, status] as const,
  stockCount: (restaurantId: string, id: string) =>
    ["stock-count", restaurantId, id] as const,
  recipes: (restaurantId: string, menuItemId?: string) =>
    ["recipes", restaurantId, menuItemId] as const,
  recipeCost: (restaurantId: string, menuItemId: string) =>
    ["recipe-cost", restaurantId, menuItemId] as const,
  lowStockReport: (restaurantId: string) =>
    ["reports", "low-stock", restaurantId] as const,
  consumptionReport: (restaurantId: string) =>
    ["reports", "consumption", restaurantId] as const,
  wasteReport: (restaurantId: string, days: number) =>
    ["reports", "waste", restaurantId, days] as const,
  expiringBatchesReport: (restaurantId: string, days: number) =>
    ["reports", "expiring-batches", restaurantId, days] as const,
};

function useRestaurantContext() {
  const { getRestaurantId, getBranchId } = useAuth();
  return {
    restaurantId: getRestaurantId(),
    branchId: getBranchId(),
  };
}

export function useIngredients(status?: string, options?: { enabled?: boolean }) {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.ingredients(restaurantId ?? "", branchId, status),
    queryFn: () => {
      const params = new URLSearchParams();
      if (status) params.set("status", status);
      if (branchId) params.set("branch_id", branchId);
      const query = params.toString();
      return api<Ingredient[]>(`/api/v1/inventory/ingredients${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
    staleTime: 30_000,
  });
}

export function useIngredient(ingredientId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.ingredient(restaurantId ?? "", ingredientId ?? "none"),
    queryFn: () => api<Ingredient>(`/api/v1/inventory/ingredients/${ingredientId}`),
    enabled: Boolean(me && ingredientId && restaurantId),
  });
}

export function useSuppliers(activeOnly = true, options?: { enabled?: boolean }) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.suppliers(restaurantId ?? "", activeOnly),
    queryFn: () => {
      const params = new URLSearchParams({ active_only: String(activeOnly) });
      return api<Supplier[]>(`/api/v1/inventory/suppliers?${params.toString()}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
    staleTime: 60_000,
  });
}

export function useSupplier(supplierId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.supplier(restaurantId ?? "", supplierId ?? "none"),
    queryFn: () => api<Supplier>(`/api/v1/inventory/suppliers/${supplierId}`),
    enabled: Boolean(me && supplierId && restaurantId),
  });
}

export function usePurchaseOrders(status?: string, options?: { enabled?: boolean }) {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.purchaseOrders(restaurantId ?? "", branchId, status),
    queryFn: () => {
      const params = new URLSearchParams();
      if (status) params.set("status", status);
      if (branchId) params.set("branch_id", branchId);
      const query = params.toString();
      return api<PurchaseOrder[]>(`/api/v1/inventory/purchase-orders${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
    refetchInterval: 30_000,
  });
}

export function usePurchaseOrder(poId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.purchaseOrder(restaurantId ?? "", poId ?? "none"),
    queryFn: () => api<PurchaseOrder>(`/api/v1/inventory/purchase-orders/${poId}`),
    enabled: Boolean(me && poId && restaurantId),
  });
}

export function useStockMovements(ingredientId?: string, options?: { enabled?: boolean; limit?: number }) {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.stockMovements(restaurantId ?? "", branchId, ingredientId),
    queryFn: () => {
      const params = new URLSearchParams();
      if (ingredientId) params.set("ingredient_id", ingredientId);
      if (branchId) params.set("branch_id", branchId);
      if (options?.limit) params.set("limit", String(options.limit));
      const query = params.toString();
      return api<StockMovement[]>(`/api/v1/inventory/stock-movements${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
  });
}

export function useBatches(ingredientId?: string, includeExpired = false, options?: { enabled?: boolean }) {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.batches(restaurantId ?? "", branchId, ingredientId),
    queryFn: () => {
      const params = new URLSearchParams({ include_expired: String(includeExpired) });
      if (ingredientId) params.set("ingredient_id", ingredientId);
      if (branchId) params.set("branch_id", branchId);
      const query = params.toString();
      return api<IngredientBatch[]>(`/api/v1/inventory/batches${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
  });
}

export function useBatch(batchId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.batch(restaurantId ?? "", batchId ?? "none"),
    queryFn: () => api<IngredientBatch>(`/api/v1/inventory/batches/${batchId}`),
    enabled: Boolean(me && batchId && restaurantId),
  });
}

export function useStockCounts(status?: string, options?: { enabled?: boolean }) {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.stockCounts(restaurantId ?? "", branchId, status),
    queryFn: () => {
      const params = new URLSearchParams();
      if (status) params.set("status", status);
      if (branchId) params.set("branch_id", branchId);
      const query = params.toString();
      return api<StockCount[]>(`/api/v1/inventory/stock-counts${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
  });
}

export function useStockCount(countId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.stockCount(restaurantId ?? "", countId ?? "none"),
    queryFn: () => api<StockCount>(`/api/v1/inventory/stock-counts/${countId}`),
    enabled: Boolean(me && countId && restaurantId),
  });
}

export function useRecipeIngredients(menuItemId?: string, options?: { enabled?: boolean }) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.recipes(restaurantId ?? "", menuItemId),
    queryFn: () => {
      const params = new URLSearchParams();
      if (menuItemId) params.set("menu_item_id", menuItemId);
      const query = params.toString();
      return api<RecipeIngredient[]>(`/api/v1/inventory/recipes${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
  });
}

export function useRecipeCost(menuItemId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.recipeCost(restaurantId ?? "", menuItemId ?? "none"),
    queryFn: () => api<{ ingredient_id: string; ingredient_name: string | null; quantity: number; unit_cost_minor: number; total_cost_minor: number }[]>(`/api/v1/inventory/recipes/${menuItemId}/cost`),
    enabled: Boolean(me && menuItemId && restaurantId),
  });
}

// Reports
export function useLowStockReport() {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.lowStockReport(restaurantId ?? ""),
    queryFn: () => api<LowStockReport>("/api/v1/inventory/reports/low-stock"),
    enabled: Boolean(me && restaurantId),
    refetchInterval: 60_000,
  });
}

export function useConsumptionReport() {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.consumptionReport(restaurantId ?? ""),
    queryFn: () => api<ConsumptionReport>("/api/v1/inventory/reports/consumption"),
    enabled: Boolean(me && restaurantId),
  });
}

export function useWasteReport(days = 30) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.wasteReport(restaurantId ?? "", days),
    queryFn: () => api<{ restaurant_id: string; window_days: number; event_count: number; waste: Array<{ ingredient_id: string; ingredient_name: string | null; total_wasted: number; event_count: number; unit: string | null }> }>(`/api/v1/inventory/reports/waste?days=${days}`),
    enabled: Boolean(me && restaurantId),
  });
}

export function useExpiringBatchesReport(days = 7) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: inventoryKeys.expiringBatchesReport(restaurantId ?? "", days),
    queryFn: () => api<{ restaurant_id: string; window_days: number; batches: Array<{ id: string; batch_no: string; ingredient_id: string; ingredient_name: string | null; unit: string | null; expiry_date: string; quantity: number; cost_value_minor: number; expired: boolean }> }>(`/api/v1/inventory/reports/expiring-batches?days=${days}`),
    enabled: Boolean(me && restaurantId),
  });
}

// Mutations
function useInvalidateInventory() {
  const queryClient = useQueryClient();
  const { restaurantId, branchId } = useRestaurantContext();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["ingredients", restaurantId, branchId] });
    void queryClient.invalidateQueries({ queryKey: ["suppliers", restaurantId] });
    void queryClient.invalidateQueries({ queryKey: ["purchase-orders", restaurantId, branchId] });
    void queryClient.invalidateQueries({ queryKey: ["stock-movements", restaurantId, branchId] });
    void queryClient.invalidateQueries({ queryKey: ["batches", restaurantId, branchId] });
    void queryClient.invalidateQueries({ queryKey: ["stock-counts", restaurantId, branchId] });
    void queryClient.invalidateQueries({ queryKey: ["reports", "low-stock", restaurantId] });
  };
}

export type CreateIngredientInput = {
  name: string;
  code?: string;
  sku?: string;
  unit: string;
  base_unit?: string;
  category?: string;
  unit_conversions?: Record<string, number>;
  current_stock?: number;
  minimum_stock?: number;
  cost_per_unit_minor?: number;
  storage_location?: string;
  branch_id?: string;
  supplier_id?: string;
};

export function useCreateIngredient() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: CreateIngredientInput) =>
      api<Ingredient>("/api/v1/inventory/ingredients", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export type UpdateIngredientInput = {
  name?: string;
  code?: string;
  sku?: string;
  unit?: string;
  base_unit?: string;
  category?: string;
  unit_conversions?: Record<string, number>;
  minimum_stock?: number;
  cost_per_unit_minor?: number;
  storage_location?: string;
  branch_id?: string;
  supplier_id?: string;
};

export function useUpdateIngredient() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: { ingredientId: string; data: UpdateIngredientInput }) =>
      api<Ingredient>(`/api/v1/inventory/ingredients/${input.ingredientId}`, {
        method: "PATCH",
        body: JSON.stringify(input.data),
      }),
    onSuccess: invalidate,
  });
}

export function useSetIngredientStock() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: { ingredientId: string; new_stock: number; reason: string }) =>
      api<Ingredient>(`/api/v1/inventory/ingredients/${input.ingredientId}/stock`, {
        method: "PATCH",
        body: JSON.stringify({ new_stock: input.new_stock, reason: input.reason }),
      }),
    onSuccess: invalidate,
  });
}

export type CreateSupplierInput = {
  name: string;
  contact_name?: string;
  phone?: string;
  email?: string;
  address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  tax_id?: string;
  is_active?: boolean;
  rating?: number;
  average_delivery_days?: number;
  notes?: string;
};

export function useCreateSupplier() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: CreateSupplierInput) =>
      api<Supplier>("/api/v1/inventory/suppliers", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export type CreatePurchaseOrderInput = {
  code: string;
  supplier_id: string;
  status?: string;
  expected_date?: string;
  purchase_date?: string;
  notes?: string;
  bill_photo_urls?: string[];
  supplier_is_walk_in?: boolean;
  items: Array<{
    ingredient_id: string;
    quantity: number;
    unit_price_minor: number;
  }>;
};

export function useCreatePurchaseOrder() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: CreatePurchaseOrderInput) =>
      api<PurchaseOrder>("/api/v1/inventory/purchase-orders", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export function useReceivePurchaseOrder() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (poId: string) =>
      api<PurchaseOrder>(`/api/v1/inventory/purchase-orders/${poId}/receive`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export type CreateStockMovementInput = {
  ingredient_id: string;
  movement_type: "RECEIVE" | "ADJUST" | "DEDUCT" | "WASTE" | "TRANSFER_IN" | "TRANSFER_OUT";
  quantity: number;
  reason?: string;
  reference_id?: string;
  reference_type?: string;
  batch_id?: string;
  branch_id?: string;
  idempotency_key?: string;
};

export function useCreateStockMovement() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: CreateStockMovementInput) =>
      api<StockMovement>("/api/v1/inventory/stock-movements", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export type CreateBatchInput = {
  ingredient_id: string;
  batch_no: string;
  expiry_date?: string;
  quantity: number;
  cost_per_unit_minor: number;
};

export function useCreateBatch() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: CreateBatchInput) =>
      api<IngredientBatch>("/api/v1/inventory/batches", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export type CreateStockCountInput = {
  branch_id?: string;
  count_date?: string;
  notes?: string;
  items: Array<{
    ingredient_id: string;
    expected_qty: number;
    counted_qty: number;
  }>;
};

export function useCreateStockCount() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: CreateStockCountInput) =>
      api<StockCount>("/api/v1/inventory/stock-counts", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export function useCompleteStockCount() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (countId: string) =>
      api<StockCount>(`/api/v1/inventory/stock-counts/${countId}/complete`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export type SetRecipeInput = {
  items: Array<{
    ingredient_id: string;
    quantity_per_serving: number;
    quantity_per_order?: number;
  }>;
};

export function useSetRecipe() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: { menuItemId: string; data: SetRecipeInput }) =>
      api<RecipeIngredient[]>(`/api/v1/inventory/recipes/${input.menuItemId}`, {
        method: "PUT",
        body: JSON.stringify(input.data),
      }),
    onSuccess: invalidate,
  });
}