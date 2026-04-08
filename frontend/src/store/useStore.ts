import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export interface Task {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed'
  assignee?: string
}

interface AppState {
  messages: Message[]
  tasks: Task[]
  isConnected: boolean
  
  addMessage: (message: Message) => void
  updateTask: (id: string, status: Task['status']) => void
  setConnection: (connected: boolean) => void
}

export const useStore = create<AppState>((set) => ({
  messages: [],
  tasks: [],
  isConnected: false,
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  updateTask: (id, status) => set((state) => ({
    tasks: state.tasks.map(t => t.id === id ? { ...t, status } : t)
  })),
  
  setConnection: (isConnected) => set({ isConnected })
}))
