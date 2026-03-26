import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { OT, OTStatus, OTFilterParams } from '@/types';
import * as api from '@/services/api';

/**
 * Query key factory for OT-related queries
 */
export const otKeys = {
  all: ['ots'] as const,
  lists: () => [...otKeys.all, 'list'] as const,
  list: (filters?: OTFilterParams) => [...otKeys.lists(), { filters }] as const,
  details: () => [...otKeys.all, 'detail'] as const,
  detail: (id: string) => [...otKeys.details(), id] as const,
};

/**
 * Hook to fetch list of OTs with optional filters
 */
export function useOTs(filters?: OTFilterParams) {
  return useQuery({
    queryKey: otKeys.list(filters),
    queryFn: () => api.getOTs(filters),
    refetchInterval: 30000, // Refetch every 30 seconds for real-time feel
    staleTime: 5000, // Data is fresh for 5 seconds
    retry: 1,
  });
}

/**
 * Hook to fetch a single OT by ID
 */
export function useOT(id: string) {
  return useQuery({
    queryKey: otKeys.detail(id),
    queryFn: () => api.getOTById(id),
    enabled: !!id, // Only run query if id is provided
    refetchInterval: 30000,
    staleTime: 5000,
    retry: 1,
  });
}

/**
 * Hook to update OT status with optimistic updates
 */
export function useUpdateOTStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      status,
      reason,
    }: {
      id: string;
      status: OTStatus;
      reason?: string;
    }) => api.updateOTStatus(id, status, reason),

    onMutate: async ({ id, status }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: otKeys.lists() });
      await queryClient.cancelQueries({ queryKey: otKeys.detail(id) });

      // Snapshot the previous value
      const previousLists = queryClient.getQueryData<OT[]>(otKeys.lists());
      const previousDetail = queryClient.getQueryData<OT>(otKeys.detail(id));

      // Optimistically update all OT lists
      if (previousLists) {
        queryClient.setQueryData(
          otKeys.lists(),
          previousLists.map((ot) =>
            ot.id === id ? { ...ot, status } : ot
          )
        );
      }

      // Optimistically update detail view
      if (previousDetail) {
        queryClient.setQueryData(otKeys.detail(id), {
          ...previousDetail,
          status,
        });
      }

      return { previousLists, previousDetail };
    },

    onError: (err, variables, context) => {
      // Revert on error
      if (context?.previousLists) {
        queryClient.setQueryData(otKeys.lists(), context.previousLists);
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(otKeys.detail(variables.id), context.previousDetail);
      }
    },

    onSuccess: (data) => {
      // Update specific queries with the result
      queryClient.setQueryData(otKeys.detail(data.id), data);

      // Invalidate list queries to refetch
      queryClient.invalidateQueries({ queryKey: otKeys.lists() });
    },
  });
}

/**
 * Hook to group OTs by status for Kanban board
 */
export function useOTsByStatus(filters?: OTFilterParams) {
  const { data: ots = [], isLoading, error } = useOTs(filters);

  // Group OTs by status
  const otsByStatus: Record<OTStatus, OT[]> = {
    [OTStatus.PREPLANIFICADA]: [],
    [OTStatus.PLANIFICADA]: [],
    [OTStatus.ASIGNADO_TAREA]: [],
    [OTStatus.DETENIDA]: [],
    [OTStatus.ANULADA]: [],
    [OTStatus.FINALIZADA]: [],
  };

  // Fill groups
  ots.forEach((ot) => {
    otsByStatus[ot.status].push(ot);
  });

  return {
    otsByStatus,
    isLoading,
    error,
  };
}

/**
 * Hook to create a new OT
 */
export function useCreateOT() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      externalId: string;
      projectType: string;
      status?: OTStatus;
      clienteName?: string;
      loginId?: string;
      lat?: number;
      long?: number;
    }) => api.createOT(data),

    onSuccess: () => {
      // Invalidate OT lists to refetch
      queryClient.invalidateQueries({ queryKey: otKeys.lists() });
    },
  });
}

/**
 * Hook to update OT fields
 */
export function useUpdateOT() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: {
        clienteName?: string;
        loginId?: string;
        lat?: number;
        long?: number;
      };
    }) => api.updateOT(id, data),

    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: otKeys.detail(id) });

      const previousDetail = queryClient.getQueryData<OT>(otKeys.detail(id));

      if (previousDetail) {
        queryClient.setQueryData(otKeys.detail(id), {
          ...previousDetail,
          ...data,
        });
      }

      return { previousDetail };
    },

    onError: (err, variables, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(
          otKeys.detail(variables.id),
          context.previousDetail
        );
      }
    },

    onSuccess: (data) => {
      queryClient.setQueryData(otKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: otKeys.lists() });
    },
  });
}

/**
 * Hook to get document status for an OT
 */
export function useDocumentStatus(otId: string) {
  return useQuery({
    queryKey: ['documents', otId],
    queryFn: () => api.getDocumentStatus(otId),
    enabled: !!otId,
    staleTime: 10000, // 10 seconds
    retry: 1,
  });
}

/**
 * Hook to perform bulk status updates
 */
export function useBulkUpdateOTStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (updates: Array<{ id: string; status: OTStatus }>) =>
      Promise.all(
        updates.map(({ id, status }) =>
          api.updateOTStatus(id, status)
        )
      ),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: otKeys.lists() });
    },
  });
}

/**
 * Hook to search OTs
 */
export function useSearchOTs(searchTerm: string) {
  const { data: ots = [], isLoading } = useOTs();

  const filtered = ots.filter((ot) =>
    ot.externalId.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ot.clienteName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ot.loginId?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return {
    results: filtered,
    isLoading,
    hasResults: filtered.length > 0,
  };
}

export default useOTs;

