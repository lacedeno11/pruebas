import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Cuadrilla, CuadrillaFilterParams } from '@/types';
import * as api from '@/services/api';

/**
 * Query key factory for Cuadrilla-related queries
 */
export const cuadrillaKeys = {
  all: ['cuadrillas'] as const,
  lists: () => [...cuadrillaKeys.all, 'list'] as const,
  list: (filters?: CuadrillaFilterParams) => [...cuadrillaKeys.lists(), { filters }] as const,
  details: () => [...cuadrillaKeys.all, 'detail'] as const,
  detail: (id: string) => [...cuadrillaKeys.details(), id] as const,
  centroid: (id: string) => [...cuadrillaKeys.detail(id), 'centroid'] as const,
};

/**
 * Hook to fetch list of cuadrillas with optional filters
 */
export function useCuadrillas(filters?: CuadrillaFilterParams) {
  return useQuery({
    queryKey: cuadrillaKeys.list(filters),
    queryFn: () => api.getCuadrillas(filters),
    refetchInterval: 30000, // Refetch every 30 seconds for real-time load tracking
    staleTime: 5000, // Data is fresh for 5 seconds
    retry: 1,
  });
}

/**
 * Hook to fetch a single cuadrilla by ID with assigned OTs
 */
export function useCuadrilla(id: string) {
  return useQuery({
    queryKey: cuadrillaKeys.detail(id),
    queryFn: () => api.getCuadrillaById(id),
    enabled: !!id, // Only run query if id is provided
    refetchInterval: 30000,
    staleTime: 5000,
    retry: 1,
  });
}

/**
 * Hook to fetch centroid for a cuadrilla
 */
export function useCuadrillaCentroid(id: string) {
  return useQuery({
    queryKey: cuadrillaKeys.centroid(id),
    queryFn: () => api.getCuadrillaCentroid(id),
    enabled: !!id,
    staleTime: 10000, // 10 seconds, less frequent than detail
    retry: 1,
  });
}

/**
 * Hook combining cuadrilla detail with centroid data
 */
export function useCuadrillaWithCentroid(id: string) {
  const { data: cuadrilla, isLoading: isLoadingDetail, error: detailError } =
    useCuadrilla(id);
  const { data: centroidData, isLoading: isLoadingCentroid, error: centroidError } =
    useCuadrillaCentroid(id);

  return {
    cuadrilla,
    centroid: centroidData?.centroid || null,
    isLoading: isLoadingDetail || isLoadingCentroid,
    error: detailError || centroidError,
    centroidData,
  };
}

/**
 * Hook to create a new cuadrilla
 */
export function useCreateCuadrilla() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name: string;
      type: string;
      dailyCapacity?: number;
    }) => api.createCuadrilla(data),

    onSuccess: () => {
      // Invalidate cuadrilla lists to refetch
      queryClient.invalidateQueries({ queryKey: cuadrillaKeys.lists() });
    },
  });
}

/**
 * Hook to update a cuadrilla
 */
export function useUpdateCuadrilla() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: {
        name?: string;
        isActive?: boolean;
        dailyCapacity?: number;
      };
    }) => api.updateCuadrilla(id, data),

    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: cuadrillaKeys.detail(id) });

      const previousDetail = queryClient.getQueryData<Cuadrilla>(
        cuadrillaKeys.detail(id)
      );

      if (previousDetail) {
        queryClient.setQueryData(cuadrillaKeys.detail(id), {
          ...previousDetail,
          ...data,
        });
      }

      return { previousDetail };
    },

    onError: (err, variables, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(
          cuadrillaKeys.detail(variables.id),
          context.previousDetail
        );
      }
    },

    onSuccess: (data) => {
      queryClient.setQueryData(cuadrillaKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: cuadrillaKeys.lists() });
    },
  });
}

/**
 * Hook to fetch all cuadrillas with their assigned OT counts
 */
export function useCuadrillasWithLoad(filters?: CuadrillaFilterParams) {
  const { data: cuadrillas = [], isLoading, error } = useCuadrillas(filters);

  // Enrich with load statistics
  const enrichedCuadrillas = cuadrillas.map((c) => ({
    ...c,
    assignedOTsCount: c.ots?.length || 0,
    loadPercentage: c.dailyCapacity > 0 ? (c.currentLoad / c.dailyCapacity) * 100 : 0,
    isAtCapacity: c.currentLoad >= c.dailyCapacity,
  }));

  return {
    cuadrillas: enrichedCuadrillas,
    isLoading,
    error,
  };
}

/**
 * Hook to get all active cuadrillas sorted by load
 */
export function useActiveCuadrillas() {
  const { cuadrillas, isLoading, error } = useCuadrillasWithLoad({
    isActive: true,
  });

  // Sort by load percentage (ascending - less loaded first)
  const sorted = [...cuadrillas].sort(
    (a, b) => a.loadPercentage - b.loadPercentage
  );

  return {
    cuadrillas: sorted,
    isLoading,
    error,
  };
}

export default useCuadrillas;

