const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        message: 'Unknown error',
      }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // 获取团队状态
  async getTeamStatus() {
    return this.request('/team');
  }

  // 获取任务图
  async getTaskGraph() {
    return this.request('/tasks');
  }

  // 获取协议列表
  async getProtocols() {
    return this.request('/protocols');
  }

  // 认领任务
  async claimTask(taskId: number) {
    return this.request('/tasks/claim', {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId }),
    });
  }

  // 发送团队消息
  async sendMessage(to: string, content: string, msgType?: string) {
    return this.request('/messages', {
      method: 'POST',
      body: JSON.stringify({ to, content, msg_type: msgType }),
    });
  }

  // 健康检查
  async healthCheck() {
    return this.request<{ status: string }>('/health');
  }

  // 发送消息（非流式）
  async postChat(content: string) {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message: content, role: 'user' }),
    });
  }

  // 审批 plan
  async approvePlan(requestId: string, approve: boolean, reason?: string) {
    return this.request('/plans/approve', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, approve, reason }),
    });
  }

  // 响应 shutdown request
  async respondToShutdown(requestId: string, approve: boolean, reason?: string) {
    return this.request('/shutdown/respond', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, approve, reason }),
    });
  }
}

export const apiClient = new ApiClient();
