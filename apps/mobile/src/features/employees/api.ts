import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Employee, Shift, ShiftAssignment } from "@rest/api-client";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const employeeKeys = {
  employees: (restaurantId: string, branchId: string | null, activeOnly?: boolean) =>
    ["employees", restaurantId, branchId, activeOnly] as const,
  employee: (restaurantId: string, id: string) =>
    ["employee", restaurantId, id] as const,
  shifts: (restaurantId: string, branchId: string | null, date?: string) =>
    ["shifts", restaurantId, branchId, date] as const,
  shift: (restaurantId: string, id: string) =>
    ["shift", restaurantId, id] as const,
  shiftAssignments: (restaurantId: string, shiftId: string) =>
    ["shift-assignments", restaurantId, shiftId] as const,
};

function useRestaurantContext() {
  const { getRestaurantId, getBranchId } = useAuth();
  return {
    restaurantId: getRestaurantId(),
    branchId: getBranchId(),
  };
}

export function useEmployees(activeOnly = false, options?: { enabled?: boolean }) {
  const { me } = useAuth();
  const { restaurantId, branchId } = useRestaurantContext();
  return useQuery({
    queryKey: employeeKeys.employees(restaurantId ?? "", branchId, activeOnly),
    queryFn: () => {
      const params = new URLSearchParams({ active_only: String(activeOnly) });
      if (branchId) params.set("branch_id", branchId);
      return api<Employee[]>(`/api/v1/employees?${params.toString()}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
    staleTime: 30_000,
  });
}

export function useEmployee(employeeId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: employeeKeys.employee(restaurantId ?? "", employeeId ?? "none"),
    queryFn: () => api<Employee>(`/api/v1/employees/${employeeId}`),
    enabled: Boolean(me && employeeId && restaurantId),
  });
}

export function useShifts(branchId?: string, date?: string, options?: { enabled?: boolean }) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: employeeKeys.shifts(restaurantId ?? "", branchId ?? null, date),
    queryFn: () => {
      const params = new URLSearchParams();
      if (branchId) params.set("branch_id", branchId);
      if (date) params.set("date", date);
      const query = params.toString();
      return api<Shift[]>(`/api/v1/shifts${query ? `?${query}` : ""}`);
    },
    enabled: Boolean(me && restaurantId) && (options?.enabled ?? true),
    refetchInterval: 60_000,
  });
}

export function useShift(shiftId: string | undefined) {
  const { me } = useAuth();
  const { restaurantId } = useRestaurantContext();
  return useQuery({
    queryKey: employeeKeys.shift(restaurantId ?? "", shiftId ?? "none"),
    queryFn: () => api<Shift>(`/api/v1/shifts/${shiftId}`),
    enabled: Boolean(me && shiftId && restaurantId),
  });
}

// Mutations
function useInvalidateEmployees() {
  const queryClient = useQueryClient();
  const { restaurantId, branchId } = useRestaurantContext();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["employees", restaurantId, branchId] });
    void queryClient.invalidateQueries({ queryKey: ["shifts", restaurantId, branchId] });
  };
}

export type CreateEmployeeInput = {
  name: string;
  email: string;
  phone?: string;
  role?: string;
  hire_date: string;
  is_active?: boolean;
  branch_id?: string;
};

export function useCreateEmployee() {
  const invalidate = useInvalidateEmployees();
  return useMutation({
    mutationFn: (input: CreateEmployeeInput) =>
      api<Employee>("/api/v1/employees", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export type UpdateEmployeeInput = {
  name?: string;
  email?: string;
  phone?: string;
  role?: string;
  hire_date?: string;
  is_active?: boolean;
  branch_id?: string;
};

export function useUpdateEmployee() {
  const invalidate = useInvalidateEmployees();
  return useMutation({
    mutationFn: (input: { employeeId: string; data: UpdateEmployeeInput }) =>
      api<Employee>(`/api/v1/employees/${input.employeeId}`, {
        method: "PATCH",
        body: JSON.stringify(input.data),
      }),
    onSuccess: invalidate,
  });
}

export type CreateShiftInput = {
  employee_id: string;
  branch_id: string;
  date: string;
  start_time: string;
  end_time: string;
  status?: "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "NO_SHOW";
  notes?: string;
};

export function useCreateShift() {
  const invalidate = useInvalidateEmployees();
  return useMutation({
    mutationFn: (input: CreateShiftInput) =>
      api<Shift>("/api/v1/shifts", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export type AssignShiftInput = {
  shift_id: string;
  employee_id: string;
  membership_id: string;
};

export function useAssignShift() {
  const invalidate = useInvalidateEmployees();
  return useMutation({
    mutationFn: (input: AssignShiftInput) =>
      api<ShiftAssignment>(`/api/v1/shifts/${input.shift_id}/assign`, {
        method: "POST",
        body: JSON.stringify({ employee_id: input.employee_id, membership_id: input.membership_id }),
      }),
    onSuccess: invalidate,
  });
}