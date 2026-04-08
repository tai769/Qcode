import { create } from 'zustand';
import { Message } from '../types';

interface ConnectionInfo {
  status: 'connected' | 'disconnected' | 'connecting';
  lastSeen: number;
}

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  connection: ConnectionInfo;
  
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;
  setStreaming: (streaming: boolean) => void;
  setConnection: (status: ConnectionInfo['status']) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  connection: {
    status: 'disconnected',
    lastSeen: 0,
  },
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  updateLastMessage: (content) => set((state) => {
    const messages = [...state.messages];
    if (messages.length > 0) {
      messages[messages.length - 1] = {
        ...messages[messages.length - 1],
        content: messages[messages.length - 1].content + content
      };
    }
    return { messages };
  }),
  
  setStreaming: (isStreaming) => set({ isStreaming }),
  
  setConnection: (status) => set({
    connection: {
      status,
      lastSeen: Date.now()
    }
  }),
  
  clearMessages: () => set({ messages: [] })
}));
