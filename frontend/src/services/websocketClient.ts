import { WSMessage } from '../types/ws';

export interface WSHandlers {
  onMessage?: (message: WSMessage) => void;
  onError?: (error: Event) => void;
  onClose?: () => void;
}

export function createWSClient(url: string, handlers: WSHandlers): () => void {
  const ws = new WebSocket(url);

  ws.onopen = () => {
    console.log('WebSocket connected');
  };

  ws.onmessage = (event) => {
    try {
      const message: WSMessage = JSON.parse(event.data);
      handlers.onMessage?.(message);
    } catch (e) {
      console.error('Failed to parse WS message:', e);
    }
  };

  ws.onerror = (error) => {
    handlers.onError?.(error);
  };

  ws.onclose = () => {
    handlers.onClose?.();
  };

  return () => {
    ws.close();
  };
}
