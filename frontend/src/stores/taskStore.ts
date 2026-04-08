import { create } from 'zustand';
import { Task } from '../types';

interface TaskGraph {
  tasks: Task[];
  ready: Task[];
  inProgress: Task[];
  completed: Task[];
}

interface TaskStore {
  graph: TaskGraph;
  isLoading: boolean;
  error: string | null;
  
  fetchTasks: () => Promise<void>;
  createTask: (task: Omit<Task, 'id' | 'createdAt'>) => Promise<void>;
  updateTaskStatus: (id: number, status: Task['status']) => Promise<void>;
  claimTask: (id: number, owner: string) => Promise<void>;
}

export const useTaskStore = create<TaskStore>((set) => ({
  graph: {
    tasks: [],
    ready: [],
    inProgress: [],
    completed: []
  },
  isLoading: false,
  error: null,
  
  fetchTasks: async () => {
    set({ isLoading: true, error: null });
    try {
      // TODO: Implement actual API call
      set({ isLoading: false });
    } catch (error: unknown) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },
  
  createTask: async (task) => {
    try {
      const newTask: Task = {
        ...task,
        id: Date.now(),
        createdAt: new Date()
      };
      set((state) => ({
        graph: {
          ...state.graph,
          tasks: [...state.graph.tasks, newTask],
          ready: [...state.graph.ready, newTask]
        }
      }));
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  },
  
  updateTaskStatus: async (id, status) => {
    try {
      set((state) => ({
        graph: {
          ...state.graph,
          tasks: state.graph.tasks.map((t: Task) =>
            t.id === id ? { ...t, status } : t
          )
        }
      }));
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  },
  
  claimTask: async (id, owner) => {
    try {
      set((state) => ({
        graph: {
          ...state.graph,
          tasks: state.graph.tasks.map((t: Task) =>
            t.id === id ? { ...t, owner, status: 'in_progress' as Task['status'] } : t
          )
        }
      }));
    } catch (error) {
      console.error('Failed to claim task:', error);
    }
  }
}));

