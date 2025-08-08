import { Chat } from '../types';

export const API_URL = '/chat-api';
export const WS_URL = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/chat-api';

// Global WebSocket instance and reconnection management
let chatWebSocket: WebSocket | null = null;
let wsConnectionPromise: Promise<WebSocket> | null = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 3;
let reconnectTimeoutId: NodeJS.Timeout | null = null;
// Mutex for connection synchronization
let connectionMutex = false;


// WebSocket connection management with reconnection
const connectWebSocket = (): Promise<WebSocket> => {
  // Return existing promise if connection is in progress or established
  if (wsConnectionPromise) {
    return wsConnectionPromise;
  }

  // Check if already trying to connect (race condition protection)
  if (connectionMutex) {
    // Wait a bit and retry to get the connection promise
    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (wsConnectionPromise) {
          clearInterval(checkInterval);
          resolve(wsConnectionPromise);
        } else if (!connectionMutex) {
          // Mutex was released without creating a connection, try again
          clearInterval(checkInterval);
          resolve(connectWebSocket());
        }
      }, 10);
    });
  }

  // Acquire mutex before creating connection
  connectionMutex = true;

  // Double-check pattern: verify promise wasn't created while waiting for mutex
  if (wsConnectionPromise) {
    connectionMutex = false;
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
      connectionMutex = false; // Release mutex on successful connection
      if (reconnectTimeoutId) {
        clearTimeout(reconnectTimeoutId);
        reconnectTimeoutId = null;
      }
      resolve(ws);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      wsConnectionPromise = null;
      connectionMutex = false; // Release mutex on error
      reject(error);
    };
    
    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      chatWebSocket = null;
      wsConnectionPromise = null;
      connectionMutex = false; // Release mutex on close
      
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
  connectionMutex = false; // Reset mutex on manual disconnect
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
    model?: string,
    isComplete?: boolean
  }) => void,
): Promise<void> => {
  const ws = await connectWebSocket();
  
  // Track accumulated content for streaming
  let accumulatedContent = '';
  let currentMessageId = '';
  
  // Wrap in a Promise to properly handle completion and cleanup
  return new Promise<void>((resolve, reject) => {
    let isCompleted = false;
    
    // Set up message listener for this request
    const messageListener = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle error messages
        if (data.type === 'error') {
          console.error('WebSocket error:', data.message);
          isCompleted = true;
          ws.removeEventListener('message', messageListener);
          reject(new Error(data.message));
          return;
        }
        
        // Handle streaming delta messages from serving endpoint
        if (data.type === 'response.output_text.delta') {
          // Set message ID from first delta
          if (data.item_id && !currentMessageId) {
            currentMessageId = data.item_id;
          }
          
          // Accumulate content from delta
          if (data.delta) {
            accumulatedContent += data.delta;
          }
          
          // Send accumulated content to UI
          const chunkData = {
            message_id: currentMessageId,
            content: accumulatedContent,
            sources: undefined,
            metrics: undefined,
            model: servingEndpointName,
            isComplete: false
          };
          onChunk(chunkData);
          return;
        }
        
        // Handle completion messages
        if (data.type === 'response.output_item.done') {
          // Final message with complete content and sources
          if (data.item && data.item.content && data.item.content[0]) {
            const finalContent = data.item.content[0].text;
            
            // Check if final content includes <think> tags
            const finalHasThink = finalContent.includes('<think>');
            const accumulatedHasThink = accumulatedContent.includes('<think>');
            
            // Use accumulated content if it has thinking and final doesn't, otherwise use final
            const contentToUse = (accumulatedHasThink && !finalHasThink) ? accumulatedContent : finalContent;
            
            const finalChunkData = {
              message_id: currentMessageId || data.item.id,
              content: contentToUse,
              sources: [], // TODO: extract sources if available
              metrics: undefined, // TODO: extract metrics if available
              model: servingEndpointName,
              isComplete: true
            };
            onChunk(finalChunkData);
          }
          
          // Mark as completed and clean up
          isCompleted = true;
          ws.removeEventListener('message', messageListener);
          resolve();
          return;
        }
        
        // Handle any other message format (fallback)
        onChunk({
          message_id: data.message_id || currentMessageId,
          content: data.content || accumulatedContent,
          sources: data.sources,
          metrics: data.metrics,
          model: data.model || servingEndpointName,
          isComplete: data.isComplete
        });
        
        // If this was a complete message, clean up
        if (data.isComplete) {
          isCompleted = true;
          ws.removeEventListener('message', messageListener);
          resolve();
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
        isCompleted = true;
        ws.removeEventListener('message', messageListener);
        reject(e);
      }
    };
    
    // Add timeout to prevent hanging forever
    const timeoutId = setTimeout(() => {
      if (!isCompleted) {
        console.error('WebSocket message timeout');
        ws.removeEventListener('message', messageListener);
        reject(new Error('Message processing timeout'));
      }
    }, 300000); // 5 minute timeout
    
    // Clean up timeout on completion
    const originalResolve = resolve;
    const originalReject = reject;
    resolve = () => {
      clearTimeout(timeoutId);
      originalResolve();
    };
    reject = (error) => {
      clearTimeout(timeoutId);
      originalReject(error);
    };
    
    ws.addEventListener('message', messageListener);
    
    // Send the message
    const messageRequest = {
      content,
      session_id: sessionId,
      include_history: includeHistory,
      serving_endpoint_name: servingEndpointName
    };
    
    try {
      ws.send(JSON.stringify(messageRequest));
    } catch (error) {
      ws.removeEventListener('message', messageListener);
      clearTimeout(timeoutId);
      reject(error);
    }
  });
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
