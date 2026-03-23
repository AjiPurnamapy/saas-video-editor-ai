import { create } from "zustand";

// =============================================================================
// UI Store — client-side state for modals, sidebar, upload
// =============================================================================

interface UIState {
  // Sidebar
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  // Upload dialog
  uploadDialogOpen: boolean;
  setUploadDialogOpen: (open: boolean) => void;

  // Upload progress
  uploadProgress: number;
  setUploadProgress: (progress: number) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  uploadDialogOpen: false,
  setUploadDialogOpen: (open) => set({ uploadDialogOpen: open }),

  uploadProgress: 0,
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
}));
