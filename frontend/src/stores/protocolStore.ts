import { create } from 'zustand';
import { Protocol } from '@/types';

interface ProtocolState {
  protocols: Protocol[];
  selectedProtocol: Protocol | null;

  // Actions
  setProtocols: (protocols: Protocol[]) => void;
  selectProtocol: (protocol: Protocol | null) => void;
  approveProtocol: (protocolId: string, feedback?: string) => Promise<void>;
  rejectProtocol: (protocolId: string, reason: string) => Promise<void>;
  fetchProtocols: () => Promise<void>;
}

export const useProtocolStore = create<ProtocolState>((set, get) => ({
  protocols: [],
  selectedProtocol: null,

  setProtocols: (protocols) => {
    set({ protocols });
  },

  selectProtocol: (protocol) => {
    set({ selectedProtocol: protocol });
  },

  approveProtocol: async (protocolId, feedback) => {
    try {
      const response = await fetch(`http://localhost:8000/api/protocols/${protocolId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback }),
      });

      if (!response.ok) {
        throw new Error('Failed to approve protocol');
      }

      await get().fetchProtocols();
    } catch (error) {
      console.error('Error approving protocol:', error);
      throw error;
    }
  },

  rejectProtocol: async (protocolId, reason) => {
    try {
      const response = await fetch(`http://localhost:8000)}/${protocolId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });

      if (!response.ok) {
        throw new Error('Failed to reject protocol');
      }

      await get().fetchProtocols();
    } catch (error) {
      console.error('Error rejecting protocol:', error);
      throw error;
    }
  },

  fetchProtocols: async () => {
    try {
      const response = await fetch('http://localhost:8000/api/protocols');
      if (!response.ok) {
        throw new Error('Failed to fetch protocols');
      }

      const protocols: Protocol[] = await response.json();
      set({ protocols });
    } catch (error) {
      console.error('Error fetching protocols:', error);
    }
  },
}));
