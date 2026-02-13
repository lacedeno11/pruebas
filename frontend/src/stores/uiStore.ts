import { create } from 'zustand';
import { UIState } from '@/types';

/**
 * Zustand store for managing UI application state
 * Handles: selected OT, sidebar visibility, map center/zoom
 */
export const useUIStore = create<UIState>((set) => ({
  // Initial state
  selectedOTId: undefined,
  sidebarOpen: true,
  mapCenter: {
    lat: -1.831239, // Ecuador center
    lng: -78.183406,
    zoom: 7,
  },

  // Actions
  setSelectedOT: (otId?: string) => {
    set({ selectedOTId: otId });
  },

  toggleSidebar: () => {
    set((state) => ({ sidebarOpen: !state.sidebarOpen }));
  },

  setMapCenter: (lat: number, lng: number, zoom: number) => {
    set({
      mapCenter: {
        lat,
        lng,
        zoom,
      },
    });
  },
}));

export default useUIStore;

