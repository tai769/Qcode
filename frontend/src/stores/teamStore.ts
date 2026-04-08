import { create } from 'zustand';
import { Teammate } from '../types';

interface TeamState {
  teammates: Teammate[];
  currentUserId: string | null;
  isLoading: boolean;
  
  fetchTeammates: () => Promise<void>;
  setCurrentUser: (id: string) => void;
  addTeammate: (teammate: Teammate) => void;
  updateTeammateStatus: (id: string, status: Teammate['status']) => void;
}

export const useTeamStore = create<TeamState>((set) => ({
  teammates: [],
  currentUserId: null,
  isLoading: false,
  
  fetchTeammates: async () => {
    set({ isLoading: true });
    try {
      // TODO: Implement actual API call
      set({ isLoading: false });
    } catch (error) {
      console.error('Failed to fetch teammates:', error);
      set({ isLoading: false });
    }
  },
  
  setCurrentUser: (id) => set({ currentUserId: id }),
  
  addTeammate: (teammate) => set((state) => ({
    teammates: [...state.teammates, teammate]
  })),
  
  updateTeammateStatus: (id, status) => set((state) => ({
    teammates: state.teammates.map((t) =>
      t.id === id ? { ...t, status } : t
    )
  }))
}));
