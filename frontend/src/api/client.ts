const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ApiMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export class ApiClient {
  async chat(messages: ApiMessage[]): Promise<string> {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages })
    });
    if (!response.ok) throw new Error(`API Error: ${response.status}`);
    const data = await response.json();
    return data.response;
  }

  async getHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const apiClient = new ApiClient();
