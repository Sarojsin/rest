import '@testing-library/jest-native/extend-expect';
import { renderHook } from '@testing-library/react';
import { waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useEmployees, useEmployee, useCreateEmployee, useUpdateEmployee, useCreateShift, useAssignShift } from '@/features/employees/api';
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

describe('employees API hooks', () => {
  describe('useEmployees', () => {
    it('fetches employees list', async () => {
      const { result } = renderHook(() => useEmployees(), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data).toHaveLength(2);
      expect(data[0]!.name).toBe('John Smith');
      expect(data[0]!.role).toBe('WAITER');
      expect(data[1]!.role).toBe('KITCHEN');
    });

    it('filters active employees only', async () => {
      const { result } = renderHook(() => useEmployees(true), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      const data = result.current.data!;
      expect(data).toHaveLength(2);
    });
  });

  describe('useEmployee', () => {
    it('fetches single employee', async () => {
      const { result } = renderHook(() => useEmployee('employee-1'), { wrapper: createWrapper() });
      
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      expect(result.current.data?.id).toBe('employee-1');
      expect(result.current.data?.name).toBe('John Smith');
    });

    it('returns null when id is undefined', async () => {
      const { result } = renderHook(() => useEmployee(undefined), { wrapper: createWrapper() });
      
      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('useCreateEmployee', () => {
    it('creates new employee', async () => {
      const { result } = renderHook(() => useCreateEmployee(), { wrapper: createWrapper() });
      
      const newEmployee = {
        name: 'Bob Wilson',
        email: 'bob@restaurant.com',
        phone: '+1-555-0103',
        role: 'CASHIER',
        hire_date: '2024-12-01T00:00:00Z',
        is_active: true,
        branch_id: 'branch-1',
      };

      await waitFor(() => {
        result.current.mutateAsync(newEmployee);
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.name).toBe('Bob Wilson');
      expect(result.current.data?.id).toBe('new-employee-1');
    });
  });

  describe('useUpdateEmployee', () => {
    it('updates existing employee', async () => {
      const { result } = renderHook(() => useUpdateEmployee(), { wrapper: createWrapper() });
      
      await waitFor(() => {
        result.current.mutateAsync({
          employeeId: 'employee-1',
          data: { role: 'MANAGER', phone: '+1-555-0199' },
        });
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.role).toBe('MANAGER');
      expect(result.current.data?.phone).toBe('+1-555-0199');
    });
  });

  describe('useCreateShift', () => {
    it('creates new shift', async () => {
      const { result } = renderHook(() => useCreateShift(), { wrapper: createWrapper() });
      
      const newShift = {
        employee_id: 'employee-1',
        branch_id: 'branch-1',
        date: '2024-12-15',
        start_time: '10:00',
        end_time: '18:00',
        status: 'SCHEDULED' as const,
        notes: 'Lunch shift',
      };

      await waitFor(() => {
        result.current.mutateAsync(newShift);
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.employee_id).toBe('employee-1');
      expect(result.current.data?.id).toBe('new-shift-1');
    });
  });

  describe('useAssignShift', () => {
    it('assigns shift to employee', async () => {
      const { result } = renderHook(() => useAssignShift(), { wrapper: createWrapper() });
      
      await waitFor(() => {
        result.current.mutateAsync({
          shift_id: 'shift-1',
          employee_id: 'employee-2',
          membership_id: 'membership-1',
        });
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.shift_id).toBe('shift-1');
      expect(result.current.data?.employee_id).toBe('employee-2');
      expect(result.current.data?.accepted_by_employee).toBe(false);
    });
  });
});