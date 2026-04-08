import { SSEEvent } from '../types';

export class SSEService {
  private eventSource: EventSource | null = null;
  private listeners: Map<string, Set<(data: unknown) => void>> = new Map();

  connect(url: string): void {
    if (this.eventSource) {
      this.disconnect();
    }

    this.eventSource = new EventSource(url);

    this.eventSource.addEventListener('open', () => {
      console.log('SSE connected');
    });

    this.eventSource.addEventListener('error', () => {
      console.error('SSE error');
    });

    this.eventSource.addEventListener('message', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as SSEEvent;
        this.notifyListeners(data);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    });
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  subscribe(eventType: string, callback: (data: unknown) => void): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    return () => {
      this.listeners.get(eventType)?.delete(callback);
    };
  }

  private notifyListeners(event: SSEEvent): void {
    const listeners = this.listeners.get(event.type);
    if (listeners) {
      listeners.forEach(callback => callback(event.data));
    }
  }
}

export const sseService = new SSEService();
