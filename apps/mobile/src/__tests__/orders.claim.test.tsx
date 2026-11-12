import '@testing-library/jest-native/extend-expect';
import { renderHook } from '@testing-library/react';
import { waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useClaimOrder, useEscalateOrder } from '@/features/orders/api';
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

describe('orders claim/escalate mutations', () => {
  describe('useClaimOrder', () => {
    it('claims an order', async () => {
      const { result } = renderHook(() => useClaimOrder(), { wrapper: createWrapper() });
      
      await waitFor(() => {
        result.current.mutateAsync('order-1');
      });

      expect(result.current.isSuccess).toBe(true);
      const data = result.current.data!;
      expect(data.id).toBe('order-1');
      expect(data.claim_state).toBe('CLAIMED');
      expect(data.claimed_by_membership_id).toBe('membership-1');
      expect(data.claimed_at).toBeDefined();
    });
  });

  describe('useEscalateOrder', () => {
    it('escalates an order', async () => {
      const { result } = renderHook(() => useEscalateOrder(), { wrapper: createWrapper() });
      
      await waitFor(() => {
        result.current.mutateAsync('order-1');
      });

      expect(result.current.isSuccess).toBe(true);
      const data = result.current.data!;
      expect(data.id).toBe('order-1');
      expect(data.claim_state).toBe('ESCALATED');
      expect(data.escalated_by_membership_id).toBe('membership-1');
      expect(data.escalated_at).toBeDefined();
    });
  });
});