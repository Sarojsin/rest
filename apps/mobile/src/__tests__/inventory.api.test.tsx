import '@testing-library/jest-native/extend-expect';
import { renderHook } from '@testing-library/react';
import { waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useIngredients, useIngredient, useCreateIngredient, useUpdateIngredient, useSetIngredientStock } from '@/features/inventory/api';
import { server } from '@/__tests__/mocks/server';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

beforeAll(() => server.listen());
afterAll(() => server.close());
afterEach(() => server.resetHandlers());

describe('inventory API hooks', () => {
  describe('useIngredients', () => {
    it('fetches ingredients list', async () => {
      const { result } = renderHook(() => useIngredients(), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data).toHaveLength(2);
      expect(data[0]!.name).toBe('Tomatoes');
      expect(data[1]!.status).toBe('LOW_STOCK');
    });

    it('filters by status', async () => {
      const { result } = renderHook(() => useIngredients('LOW_STOCK'), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data).toHaveLength(2);
    });
  });

  describe('useIngredient', () => {
    it('fetches single ingredient', async () => {
      const { result } = renderHook(() => useIngredient('ingredient-1'), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      expect(result.current.data?.id).toBe('ingredient-1');
      expect(result.current.data?.name).toBe('Tomatoes');
    });

    it('returns null when id is undefined', async () => {
      const { result } = renderHook(() => useIngredient(undefined), { wrapper: createWrapper() });
      
      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('useCreateIngredient', () => {
    it('creates new ingredient', async () => {
      const { result } = renderHook(() => useCreateIngredient(), { wrapper: createWrapper() });
      
      const newIngredient = {
        name: 'Lettuce',
        code: 'LET',
        sku: 'SKU-LET-001',
        unit: 'kg',
        base_unit: 'kg',
        category: 'Vegetables',
        current_stock: 20,
        minimum_stock: 5,
        cost_per_unit_minor: 150,
        storage_location: 'Walk-in Cooler A',
        branch_id: 'branch-1',
        supplier_id: 'supplier-1',
      };

      await waitFor(() => {
        result.current.mutateAsync(newIngredient);
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.name).toBe('Lettuce');
      expect(result.current.data?.id).toBe('new-ingredient-1');
    });
  });

  describe('useUpdateIngredient', () => {
    it('updates existing ingredient', async () => {
      const { result } = renderHook(() => useUpdateIngredient(), { wrapper: createWrapper() });
      
      await waitFor(() => {
        result.current.mutateAsync({
          ingredientId: 'ingredient-1',
          data: { name: 'Organic Tomatoes', minimum_stock: 15 },
        });
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.name).toBe('Organic Tomatoes');
      expect(result.current.data?.minimum_stock).toBe(15);
    });
  });

  describe('useSetIngredientStock', () => {
    it('updates ingredient stock level', async () => {
      const { result } = renderHook(() => useSetIngredientStock(), { wrapper: createWrapper() });
      
      await waitFor(() => {
        result.current.mutateAsync({
          ingredientId: 'ingredient-1',
          new_stock: 75,
          reason: 'Restocked from delivery',
        });
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.current_stock).toBe(75);
      expect(result.current.data?.status).toBe('IN_STOCK');
    });

    it('sets status to LOW_STOCK when below minimum', async () => {
      const { result } = renderHook(() => useSetIngredientStock(), { wrapper: createWrapper() });
      
      await waitFor(() => {
        result.current.mutateAsync({
          ingredientId: 'ingredient-1',
          new_stock: 5,
          reason: 'Used in prep',
        });
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.current_stock).toBe(5);
      expect(result.current.data?.status).toBe('LOW_STOCK');
    });
  });
});