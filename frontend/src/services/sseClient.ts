export interface SSEHandlers {
  onConnected?: () => void;
  onMessage?: (data: unknown) => void;
  onError?: (error: Event) => void;
}

export function createSSEClient(url: string, handlers: SSEHandlers): () => void {
  const eventSource = new EventSource(url);

  eventSource.addEventListener('open', () => {
    handlers.onConnected?.();
  });

  eventSource.addEventListener('error', (error) => {
    handlers.onError?.(error as Event);
    eventSource.close();
  });

  eventSource.addEventListener('message', (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      handlers.onMessage?.(data);
    } catch (e) {
      console.error('Failed to parse SSE message:', e);
    }
  });

  return () => {
    eventSource.close();
  };
}
