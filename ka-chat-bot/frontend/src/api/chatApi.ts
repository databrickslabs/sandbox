import { Chat } from '../types';

export const API_URL = '/chat-api';


export const sendMessage = async (
  content: string, 
  sessionId: string,
  includeHistory: boolean,
  servingEndpointName: string,
  onChunk: (chunk: { 
    message_id: string,
    content?: string, 
    sources?: any[],
    metrics?: {
      timeToFirstToken?: number;
      totalTime?: number;
    },
    model?: string
  }) => void,
): Promise<void> => {
  try {
    const response = await fetch(
      `${API_URL}/chat`, 
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ 
          content,
          session_id: sessionId,
          include_history: includeHistory,
          serving_endpoint_name: servingEndpointName
        })
      }
    );
    if (!response.ok) {
      console.log("response.ok", response.ok);
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      console.log("No reader available");
      throw new Error('No reader available');
    }

    const decoder = new TextDecoder();
    let accumulatedContent = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6);
          if (jsonStr && jsonStr !== '{}') {
            try {
              const data = JSON.parse(jsonStr);
              // Double parse if the first parse returned a string
              const parsedData = typeof data === 'string' ? JSON.parse(data) : data;
              
              if (parsedData.content) {
                accumulatedContent += parsedData.content;
              }
              onChunk({
                message_id: parsedData.message_id,
                content: accumulatedContent,
                sources: parsedData.sources,
                metrics: parsedData.metrics
              });
            } catch (e) {
              console.error('Error parsing JSON:', e);
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};

export const getChatHistory = async (): Promise<{ sessions: Chat[] }> => {
  try {
    const response = await fetch(`${API_URL}/chats`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching chat history:', error);
    return { sessions: [] };
  }
};

export const regenerateMessage = async (
  content: string,
  sessionId: string,
  messageId: string,
  includeHistory: boolean,
  servingEndpointName: string,
  onChunk: (chunk: {
    content?: string,
    sources?: any[],
    metrics?: {
      timeToFirstToken?: number;
      totalTime?: number;
    }
  }) => void
): Promise<void> => {
  try {
    const response = await fetch(
      `${API_URL}/regenerate`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ 
          message_id: messageId,
          original_content: content,
          session_id: sessionId,
          include_history: includeHistory,
          serving_endpoint_name: servingEndpointName
        })
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No reader available');

    const decoder = new TextDecoder();
    let accumulatedContent = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6);
          if (jsonStr && jsonStr !== '{}') {
            try {
              const data = JSON.parse(jsonStr);
              if (data.content) {
                accumulatedContent += data.content;
              }
              onChunk({
                ...data,
                content: accumulatedContent // Send accumulated content instead of just the chunk
              });
            } catch (e) {
              console.error('Error parsing JSON:', e);
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('Error regenerating message:', error);
    throw error;
  }
};

export const fetchUserInfo = async (): Promise<{ username: string; email: string, displayName: string }> => {
  try {
    const response = await fetch(`${API_URL}/user-info`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching user info:', error);
    throw error;
  }
};


export const logout = async () => {
  window.location.href = `${API_URL}/logout`;
};

export interface ServingEndpoint {
  name: string;
  state: string;
}
