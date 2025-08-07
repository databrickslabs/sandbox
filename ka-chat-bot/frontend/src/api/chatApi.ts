import { Chat } from '../types';

export const API_URL = '/chat-api';
export const WS_URL = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/chat-api';

// Global WebSocket instance and reconnection management
let chatWebSocket: WebSocket | null = null;
let wsConnectionPromise: Promise<WebSocket> | null = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 3;
let reconnectTimeoutId: NodeJS.Timeout | null = null;

// Get token from browser (this assumes token is passed via headers by proxy)
const getToken = (): string => {
  const token = window.localStorage.getItem('auth_token') || '';
  console.log('Frontend getToken: localStorage auth_token =', token ? `${token.substring(0,20)}...` : 'EMPTY');
  
  // In remote environments, the proxy should provide the token somehow
  // Check if we can get it from anywhere else
  if (!token) {
    console.log('Frontend getToken: No token found in localStorage');
  }
  
  return token;
};

// WebSocket connection management with reconnection
const connectWebSocket = (): Promise<WebSocket> => {
  if (wsConnectionPromise) {
    return wsConnectionPromise;
  }

  wsConnectionPromise = new Promise((resolve, reject) => {
    // Token will be read from headers by the proxy, no need for query parameter
    const wsUrl = `${WS_URL}/chat-ws`;
    
    console.log('Connecting to WebSocket:', wsUrl, `(attempt ${reconnectAttempts + 1})`);
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected successfully');
      chatWebSocket = ws;
      reconnectAttempts = 0; // Reset on successful connection
      if (reconnectTimeoutId) {
        clearTimeout(reconnectTimeoutId);
        reconnectTimeoutId = null;
      }
      resolve(ws);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      wsConnectionPromise = null;
      reject(error);
    };
    
    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      chatWebSocket = null;
      wsConnectionPromise = null;
      
      // Attempt reconnection if not a manual close and we haven't exceeded max attempts
      if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000); // Exponential backoff, max 10s
        console.log(`WebSocket reconnecting in ${delay}ms...`);
        reconnectAttempts++;
        
        reconnectTimeoutId = setTimeout(() => {
          connectWebSocket();
        }, delay);
      } else if (reconnectAttempts >= maxReconnectAttempts) {
        console.warn('Max WebSocket reconnection attempts reached');
        reconnectAttempts = 0; // Reset for future connection attempts
      }
    };
  });
  
  return wsConnectionPromise;
};

const disconnectWebSocket = () => {
  // Clear any pending reconnection attempts
  if (reconnectTimeoutId) {
    clearTimeout(reconnectTimeoutId);
    reconnectTimeoutId = null;
  }
  
  if (chatWebSocket) {
    chatWebSocket.close(1000, 'Manual disconnect'); // Use 1000 to indicate normal closure
    chatWebSocket = null;
  }
  
  wsConnectionPromise = null;
  reconnectAttempts = 0;
};

// WebSocket-only sendMessage function
export const sendMessageViaWebSocket = async (
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
  const ws = await connectWebSocket();
  
  // Set up message listener for this request
  const messageListener = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      console.log('🔄 FRONTEND WS: Received message:', data);
      
      // Handle heartbeat messages - they're just for keeping connection alive
      if (data.type === 'heartbeat') {
        console.log('🔄 FRONTEND WS: Received heartbeat', data);
        return;
      }
      
      // Handle error messages
      if (data.type === 'error') {
        console.error('WebSocket error:', data.message);
        throw new Error(data.message);
      }
      
      // Handle normal chat chunks
      console.log('🔄 FRONTEND WS: Processing chat chunk:', data);
      onChunk({
        message_id: data.message_id,
        content: data.content,
        sources: data.sources,
        metrics: data.metrics,
        model: data.model
      });
    } catch (e) {
      console.error('Error parsing WebSocket message:', e);
      throw e;
    }
  };
  
  ws.addEventListener('message', messageListener);
  
  // Send the message
  const messageRequest = {
    content,
    session_id: sessionId,
    include_history: includeHistory,
    serving_endpoint_name: servingEndpointName
  };
  
  console.log('🔄 FRONTEND WS: Sending message via WebSocket:', messageRequest);
  ws.send(JSON.stringify(messageRequest));
};

// Original HTTP-based sendMessage function (renamed for clarity)
export const sendMessageViaHTTP = async (
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
              
              // Skip heartbeat messages - they're just for keeping connection alive
              if (parsedData.type === 'heartbeat') {
                console.log('🔄 FRONTEND: Received heartbeat, keeping connection alive', parsedData);
                continue;
              }
              
              // Accumulate content as delta chunks arrive
              if (parsedData.content) {
                accumulatedContent += parsedData.content;
              }
              
              // Send accumulated content to the UI for real-time streaming
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

// Main sendMessage export - uses WebSocket only
export const sendMessage = sendMessageViaWebSocket;

// Export WebSocket management functions
export { connectWebSocket, disconnectWebSocket };
