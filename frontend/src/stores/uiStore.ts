/**
 * UI State Store using Zustand
 *
 * This store manages global UI state including drag & drop state,
 * selected OT, sidebar visibility, and active view. Using Zustand
 * for lightweight, TypeScript-friendly state management.
 */

import { create } from "zustand";

/**
 * UI Store Interface
 * Defines the shape of UI state and its actions
 */
export interface UIStore {
  // State
  isDragging: boolean;
  selectedOTId: number | null;
  isSidebarOpen: boolean;
  activeView: "kanban" | "map" | "list";
  isLoading: boolean;
  error: string | null;

  // Actions
  setDragging: (isDragging: boolean) => void;
  selectOT: (otId: number | null) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
  setActiveView: (view: "kanban" | "map" | "list") => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  resetError: () => void;
  resetState: () => void;
}

/**
 * Initial state
 */
const initialState = {
  isDragging: false,
  selectedOTId: null,
  isSidebarOpen: false,
  activeView: "kanban" as const,
  isLoading: false,
  error: null,
};

/**
 * Create the UI store with Zustand
 * Handles all UI-related state that doesn't belong in React Query (server state)
 */
export const useUIStore = create<UIStore>((set) => ({
  // Initial state
  ...initialState,

  // Actions
  setDragging: (isDragging: boolean) =>
    set({ isDragging }),

  selectOT: (otId: number | null) =>
    set({ selectedOTId: otId }),

  toggleSidebar: () =>
    set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  setSidebarOpen: (isOpen: boolean) =>
    set({ isSidebarOpen: isOpen }),

  setActiveView: (view: "kanban" | "map" | "list") =>
    set({ activeView: view }),

  setLoading: (isLoading: boolean) =>
    set({ isLoading }),

  setError: (error: string | null) =>
    set({ error }),

  resetError: () =>
    set({ error: null }),

  resetState: () =>
    set(initialState),
}));

/**
 * Selector hooks for better performance
 * These prevent unnecessary re-renders by only subscribing to specific state slices
 */

export const useDraggingState = () =>
  useUIStore((state) => state.isDragging);

export const useSelectedOT = () =>
  useUIStore((state) => state.selectedOTId);

export const useSidebarOpen = () =>
  useUIStore((state) => state.isSidebarOpen);

export const useActiveView = () =>
  useUIStore((state) => state.activeView);

export const useLoadingState = () =>
  useUIStore((state) => state.isLoading);

export const useError = () =>
  useUIStore((state) => state.error);

/**
 * Combined selectors for related state
 */

export const useDragActions = () =>
  useUIStore((state) => ({
    isDragging: state.isDragging,
    setDragging: state.setDragging,
  }));

export const useViewActions = () =>
  useUIStore((state) => ({
    activeView: state.activeView,
    setActiveView: state.setActiveView,
  }));

export const useSidebarActions = () =>
  useUIStore((state) => ({
    isSidebarOpen: state.isSidebarOpen,
    toggleSidebar: state.toggleSidebar,
    setSidebarOpen: state.setSidebarOpen,
  }));

export const useOTSelection = () =>
  useUIStore((state) => ({
    selectedOTId: state.selectedOTId,
    selectOT: state.selectOT,
  }));

export const useLoadingActions = () =>
  useUIStore((state) => ({
    isLoading: state.isLoading,
    setLoading: state.setLoading,
  }));

export const useErrorHandling = () =>
  useUIStore((state) => ({
    error: state.error,
    setError: state.setError,
    resetError: state.resetError,
  }));

export default useUIStore;

