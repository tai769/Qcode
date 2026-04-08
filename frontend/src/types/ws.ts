export interface WSMessage {
  type: string;
  data?: unknown;
}

export type WSMessageType = WSMessage['type'];

export interface MessagePayload {
  content: string;
  role: 'user' | 'assistant' | 'system';
}

export interface TaskPayload {
  id: number;
  status: string;
}

export interface ProtocolPayload {
  id: string;
  status: string;
}
