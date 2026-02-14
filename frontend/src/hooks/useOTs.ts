/**
 * Custom React Query Hooks for OT Management
 *
 * This module provides reusable hooks for fetching, updating, and managing
 * OT data using React Query with optimistic updates and caching.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
  UseMutationResult,
} from "@tanstack/react-query";
import {
  fetchOTs,
  fetchOTById,
  updateOTStatus,
  validateTransition,
} from "../services/api";
import { OT, OTFilters, PaginatedResponse } from "../types";
import { useUIStore } from "../stores/uiStore";

/**
 * Query keys for React Query
 */
const otQueryKeys = {
  all: ["ots"] as const,
  lists: () => [...otQueryKeys.all, "list"] as const,
  list: (filters?: OTFilters) =>
    [...otQueryKeys.lists(), { filters }] as const,
  details: () => [...otQueryKeys.all, "detail"] as const,
  detail: (id: number) => [...otQueryKeys.details(), id] as const,
};

/**
 * Hook for fetching OTs with filtering and pagination
 *
 * @param filters Optional filters (status, project_type, cuadrilla_id, etc.)
 * @returns React Query result with OT list data
 *
 * @example
 * const { data, isLoading, error } = useOTs({
 *   status: OTStatus.PREPLANIFICADA,
 *   skip: 0,
 *   limit: 50
 * });
 */
export function useOTs(
  filters?: OTFilters
): UseQueryResult<PaginatedResponse<OT>, Error> {
  return useQuery({
    queryKey: otQueryKeys.list(filters),
    queryFn: () => fetchOTs(filters),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every 60 seconds for real-time updates
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook for fetching a single OT by ID
 *
 * @param id OT ID to fetch
 * @returns React Query result with single OT data
 *
 * @example
 * const { data: ot, isLoading } = useOTById(123);
 */
export function useOTById(id: number): UseQueryResult<OT, Error> {
  return useQuery({
    queryKey: otQueryKeys.detail(id),
    queryFn: () => fetchOTById(id),
    staleTime: 30000,
    enabled: !!id, // Only fetch if id is provided
  });
}

/**
 * Hook for updating OT status with optimistic updates
 *
 * @returns Mutation result with update status function
 *
 * @example
 * const { mutate: updateStatus, isPending } = useUpdateOTStatus();
 *
 * updateStatus({
 *   id: 123,
 *   newStatus: OTStatus.PLANIFICADA,
 *   reason: "Moving to next phase"
 * });
 */
export function useUpdateOTStatus(): UseMutationResult<
  OT,
  Error,
  { id: number; newStatus: string; reason?: string }
> {
  const queryClient = useQueryClient();
  const { setLoading, setError } = useUIStore((state) => ({
    setLoading: state.setLoading,
    setError: state.setError,
  }));

  return useMutation({
    mutationFn: ({ id, newStatus, reason }) =>
      updateOTStatus(id, newStatus, reason),

    // Optimistic update
    onMutate: async ({ id, newStatus }) => {
      setLoading(true);

      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: otQueryKeys.all });

      // Get previous data
      const previousOTs = queryClient.getQueryData<PaginatedResponse<OT>>(
        otQueryKeys.lists()
      );

      // Optimistically update cached OT list
      if (previousOTs) {
        const updatedOTs = previousOTs.data.map((ot) =>
          ot.id === id ? { ...ot, status: newStatus as any } : ot
        );

        queryClient.setQueryData(otQueryKeys.lists(), {
          ...previousOTs,
          data: updatedOTs,
        });
      }

      // Also update individual OT cache
      const previousOT = queryClient.getQueryData<OT>(
        otQueryKeys.detail(id)
      );
      if (previousOT) {
        queryClient.setQueryData(otQueryKeys.detail(id), {
          ...previousOT,
          status: newStatus,
        });
      }

      return { previousOTs, previousOT };
    },

    // Success handling
    onSuccess: (updatedOT) => {
      setLoading(false);
      setError(null);

      // Update the specific OT cache
      queryClient.setQueryData(otQueryKeys.detail(updatedOT.id), updatedOT);

      // Invalidate list to sync with server
      queryClient.invalidateQueries({ queryKey: otQueryKeys.lists() });
    },

    // Error handling
    onError: (error, variables, context) => {
      setLoading(false);
      setError(error.message || "Failed to update OT status");

      // Rollback to previous data
      if (context?.previousOTs) {
        queryClient.setQueryData(
          otQueryKeys.lists(),
          context.previousOTs
        );
      }
      if (context?.previousOT) {
        queryClient.setQueryData(
          otQueryKeys.detail(variables.id),
          context.previousOT
        );
      }
    },

    // Always refetch after mutation
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: otQueryKeys.lists() });
    },
  });
}

/**
 * Hook for validating OT status transitions
 *
 * @returns Mutation result with validation function
 *
 * @example
 * const { mutate: validate } = useValidateTransition();
 *
 * validate({
 *   otId: 123,
 *   newStatus: OTStatus.DETENIDA,
 *   reason: "Equipment failure"
 * }, {
 *   onSuccess: (result) => {
 *     if (result.valid) {
 *       // Proceed with status update
 *     }
 *   }
 * });
 */
export function useValidateTransition(): UseMutationResult<
  { valid: boolean; message: string; error?: string; requires_detention_reason?: boolean },
  Error,
  { otId: number; newStatus: string; reason?: string }
> {
  return useMutation({
    mutationFn: ({ otId, newStatus, reason }) =>
      validateTransition(otId, newStatus, reason),
  });
}

/**
 * Hook for batching multiple OT operations
 *
 * @returns Object with multiple mutation hooks
 *
 * @example
 * const { updateStatus, validate } = useOTOperations();
 */
export function useOTOperations() {
  const updateStatus = useUpdateOTStatus();
  const validate = useValidateTransition();

  return {
    updateStatus,
    validate,
  };
}

/**
 * Hook for getting OT data with loading and error states
 * Combines useOTs with UI state management
 *
 * @param filters Optional filters
 * @returns Combined OT data with UI state
 *
 * @example
 * const { ots, isLoading, error, refetch } = useOTsWithState();
 */
export function useOTsWithState(filters?: OTFilters) {
  const { data, isLoading, error, refetch } = useOTs(filters);
  const { setLoading, setError } = useUIStore((state) => ({
    setLoading: state.setLoading,
    setError: state.setError,
  }));

  // Sync loading state to UI store
  React.useEffect(() => {
    setLoading(isLoading);
  }, [isLoading, setLoading]);

  // Sync error state to UI store
  React.useEffect(() => {
    if (error) {
      setError(error.message);
    }
  }, [error, setError]);

  return {
    ots: data?.data || [],
    total: data?.total || 0,
    isLoading,
    error: error?.message || null,
    refetch,
  };
}

import React from "react";

