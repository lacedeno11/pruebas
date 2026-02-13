/**
 * React Query Configuration
 *
 * This module configures the React Query client with sensible defaults
 * for data fetching, caching, and synchronization with the backend API.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";

/**
 * Create a configured QueryClient instance
 *
 * Default options:
 * - staleTime: 30000ms (30 seconds) - Data is fresh for 30 seconds
 * - refetchOnWindowFocus: false - Don't refetch when window regains focus
 * - retry: 1 - Retry failed requests once
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      refetchOnWindowFocus: false,
      retry: 1,
      gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
    },
    mutations: {
      retry: 1,
    },
  },
});

/**
 * QueryClientProvider wrapper component
 * Wrap your app with this to enable React Query functionality
 *
 * @param children React components to wrap
 * @returns Provider component
 *
 * @example
 * <QueryClientProviderWrapper>
 *   <Dashboard />
 * </QueryClientProviderWrapper>
 */
export function QueryClientProviderWrapper({
  children,
}: {
  children: ReactNode;
}): JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

export default queryClient;

