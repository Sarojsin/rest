import '@testing-library/jest-native/extend-expect';
import { renderHook } from '@testing-library/react';
import { waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useSalesReport, useAdvancedReport, usePaymentsReport, useKitchenSpeedReport, useAuditEvents } from '@/features/reports/api';
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

describe('reports API hooks', () => {
  describe('useSalesReport', () => {
    it('fetches sales report', async () => {
      const { result } = renderHook(() => useSalesReport(), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data.currency_code).toBe('USD');
      expect(data.order_count).toBe(150);
      expect(data.accepted_order_count).toBe(145);
      expect(data.top_items).toHaveLength(2);
    });
  });

  describe('useAdvancedReport', () => {
    it('fetches advanced report with daily breakdown', async () => {
      const { result } = renderHook(() => useAdvancedReport(30), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data.window_days).toBe(30);
      expect(data.average_order_minor).toBe(8620);
      expect(data.daily).toHaveLength(2);
      expect(data.daily[0]!.date).toBe('2024-11-01');
    });
  });

  describe('usePaymentsReport', () => {
    it('fetches payments report with method breakdown', async () => {
      const { result } = renderHook(() => usePaymentsReport(30), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data.total_collected_minor).toBe(1300000);
      expect(data.succeeded_count).toBe(142);
      expect(data.failed_count).toBe(3);
      expect(data.methods).toHaveLength(2);
      expect(data.methods[0]!.method).toBe('Cash');
    });
  });

  describe('useKitchenSpeedReport', () => {
    it('fetches kitchen speed report', async () => {
      const { result } = renderHook(() => useKitchenSpeedReport(30), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data.completed_ticket_count).toBe(200);
      expect(data.avg_prep_seconds).toBe(420);
      expect(data.slowest_tickets).toHaveLength(1);
    });
  });

  describe('useAuditEvents', () => {
    it('fetches audit events', async () => {
      const { result } = renderHook(() => useAuditEvents(), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data).toHaveLength(1);
      expect(data[0]!.action).toBe('CREATE');
      expect(data[0]!.entity_type).toBe('Ingredient');
    });
  });
});