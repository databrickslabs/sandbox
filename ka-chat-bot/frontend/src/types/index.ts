export interface MessageMetrics {
  timeToFirstToken?: number;
  totalTime?: number;
}

export interface Message {
  message_id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  created_at?: Date;
  isThinking?: boolean;
  model?: string;
  sources?: any[] | null;
  metrics?: MessageMetrics | null;
}

export interface Chat {
  sessionId: string;
  firstQuery: string;
  messages: Message[];    
  timestamp: Date;
  isActive?: boolean;
} 