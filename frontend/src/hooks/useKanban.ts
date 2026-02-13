/**
 * Custom React Query Hook for Kanban Board Data
 *
 * This hook fetches and manages Kanban board data, including real-time
 * refetching to keep the board in sync with backend OT status changes.
 */

import {
  useQuery,
  UseQueryResult,
} from "@tanstack/react-query";
import { fetchKanbanData } from "../services/api";
import { KanbanData, OTStatus } from "../types";
import { useUIStore } from "../stores/uiStore";
import { useEffect } from "react";

/**
 * Query keys for Kanban data
 */
const kanbanQueryKeys = {
  all: ["kanban"] as const,
  data: () => [...kanbanQueryKeys.all, "data"] as const,
};

/**
 * Hook for fetching and managing Kanban board data
 *
 * Features:
 * - Real-time refetching every 30 seconds
 * - Automatic refetch when window regains focus
 * - Optimized caching with 30-second stale time
 * - Integrated with UI state for loading indicators
 *
 * @returns React Query result with Kanban data organized by status
 *
 * @example
 * const { data, isLoading, refetch } = useKanban();
 *
 * if (isLoading) return <div>Loading...</div>;
 *
 * return (
 *   <div>
 *     {Object.entries(data.columns).map(([status, column]) => (
 *       <KanbanColumn key={status} {...column} />
 *     ))}
 *   </div>
 * );
 */
export function useKanban(): UseQueryResult<KanbanData, Error> {
  const { setLoading, setError } = useUIStore((state) => ({
    setLoading: state.setLoading,
    setError: state.setError,
  }));

  const query = useQuery({
    queryKey: kanbanQueryKeys.data(),
    queryFn: fetchKanbanData,
    staleTime: 30000, // 30 seconds
    refetchInterval: 30000, // Refetch every 30 seconds for real-time updates
    refetchOnWindowFocus: true, // Refetch when window regains focus
    refetchIntervalInBackground: false, // Don't refetch in background
  });

  // Sync loading state to UI store
  useEffect(() => {
    setLoading(query.isLoading);
  }, [query.isLoading, setLoading]);

  // Sync error state to UI store
  useEffect(() => {
    if (query.error) {
      setError(query.error.message);
    }
  }, [query.error, setError]);

  return query;
}

/**
 * Hook for getting OTs in a specific status column
 *
 * @param status The OT status to filter by
 * @returns Array of OTs with that status
 *
 * @example
 * const preplanificadaOTs = useOTsByStatus(OTStatus.PREPLANIFICADA);
 */
export function useOTsByStatus(status: OTStatus) {
  const { data } = useKanban();

  return data?.columns[status]?.ots || [];
}

/**
 * Hook for getting all OTs across all columns
 *
 * @returns Flat array of all OTs from all status columns
 *
 * @example
 * const allOTs = useAllKanbanOTs();
 */
export function useAllKanbanOTs() {
  const { data } = useKanban();

  if (!data) return [];

  return Object.values(data.columns).flatMap((column) => column.ots);
}

/**
 * Hook for getting Kanban column counts
 *
 * @returns Object with count for each status
 *
 * @example
 * const { PREPLANIFICADA, PLANIFICADA } = useKanbanCounts();
 */
export function useKanbanCounts(): Record<OTStatus, number> {
  const { data } = useKanban();

  if (!data) {
    return {
      [OTStatus.PREPLANIFICADA]: 0,
      [OTStatus.PLANIFICADA]: 0,
      [OTStatus.ASIGNADO_TAREA]: 0,
      [OTStatus.DETENIDA]: 0,
      [OTStatus.ANULADA]: 0,
      [OTStatus.FINALIZADA]: 0,
    };
  }

  return {
    [OTStatus.PREPLANIFICADA]: data.columns[OTStatus.PREPLANIFICADA]?.count || 0,
    [OTStatus.PLANIFICADA]: data.columns[OTStatus.PLANIFICADA]?.count || 0,
    [OTStatus.ASIGNADO_TAREA]: data.columns[OTStatus.ASIGNADO_TAREA]?.count || 0,
    [OTStatus.DETENIDA]: data.columns[OTStatus.DETENIDA]?.count || 0,
    [OTStatus.ANULADA]: data.columns[OTStatus.ANULADA]?.count || 0,
    [OTStatus.FINALIZADA]: data.columns[OTStatus.FINALIZADA]?.count || 0,
  };
}

/**
 * Hook for manually refetching Kanban data
 *
 * @returns Function to trigger refetch
 *
 * @example
 * const refetch = useRefreshKanban();
 *
 * // Manually refresh Kanban board
 * await refetch();
 */
export function useRefreshKanban() {
  const { refetch } = useKanban();

  return refetch;
}

/**
 * Hook for getting Kanban data with loading and error states
 * Combines useKanban with UI state management
 *
 * @returns Combined Kanban data with UI state
 *
 * @example
 * const { columns, isLoading, error, refetch } = useKanbanWithState();
 */
export function useKanbanWithState() {
  const { data, isLoading, error, refetch } = useKanban();

  return {
    columns: data?.columns || {},
    totalCount: data?.total_count || 0,
    isLoading,
    error: error?.message || null,
    refetch,
    timestamp: data?.timestamp,
  };
}

/**
 * Hook for getting a specific OT from Kanban data
 *
 * @param otId The OT ID to find
 * @returns The OT object or undefined if not found
 *
 * @example
 * const ot = useKanbanOT(123);
 */
export function useKanbanOT(otId: number) {
  const { data } = useKanban();

  if (!data) return undefined;

  for (const column of Object.values(data.columns)) {
    const ot = column.ots.find((o) => o.id === otId);
    if (ot) return ot;
  }

  return undefined;
}

export default useKanban;

