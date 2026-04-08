import { create } from 'zustand';
import { UIState } from '../types';

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  activeTab: 'chat',
  theme: 'light',
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveTab: (tab: string) => set({ activeTab: tab }),
  setTheme: (theme: 'light' | 'dark') => set({ theme }),
}));
