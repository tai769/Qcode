export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  type?: 'chat' | 'tool' | 'system';
  content: string;
  timestamp: Date | number;
  toolCalls?: ToolCall[];
  toolOutputs?: ToolOutput[];
}

export interface SSEEvent {
  type: string;
  data?: unknown;
  event?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  args?: Record<string, unknown>;
  arguments?: Record<string, unknown>;
  status?: 'running' | 'completed' | 'error';
}

export interface ToolOutput {
  id: string;
  toolCallId: string;
  name?: string;
  output: string;
  timestamp: Date;
}

export interface Task {
  id: number;
  subject: string;
  title?: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed';
  assignee?: string;
  owner?: string;
  requiredRole?: string;
  priority: 'low' | 'medium' | 'high';
  createdAt: Date;
  blockedBy?: number[];
}

export interface ProtocolRequest {
  id: string;
  kind: 'shutdown' | 'plan_approval';
  status: 'pending' | 'approved' | 'rejected';
  teammate?: string;
  reason: string;
  createdAt: Date;
}

export interface Teammate {
  id: string;
  name: string;
  role: string;
  status: 'online' | 'busy' | 'offline' | 'idle';
  avatar?: string;
}

export interface UIState {
  sidebarOpen: boolean;
  activeTab: string;
  theme: 'light' | 'dark';
  toggleSidebar: () => void;
  setActiveTab: (tab: string) => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export interface Protocol {
  id: string;
  kind: string;
  status: string;
  teammate?: string;
  reason: string;
}

export interface TaskState {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
  fetchTasks: () => Promise<void>;
  createTask: (task: Omit<Task, 'id' | 'createdAt'>) => Promise<void>;
  updateTaskStatus: (id: number, status: Task['status']) => Promise<void>;
}
