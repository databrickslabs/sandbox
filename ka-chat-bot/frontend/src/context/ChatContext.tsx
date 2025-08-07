import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { Message, Chat } from '../types';
import { sendMessage as apiSendMessage, getChatHistory, API_URL, logout as apiLogout } from '../api/chatApi';
import { v4 as uuid } from 'uuid';

interface ChatContextType {
  currentChat: Chat | null;
  chats: Chat[];
  messages: Message[];
  loading: boolean;
  sendMessage: (content: string, includeHistory: boolean) => Promise<void>;
  selectChat: (chatId: string) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  startNewSession: () => void;
  copyMessage: (content: string) => void;
  logout: () => void;
  error: string | null;
  clearError: () => void;
  currentEndpoint: string;
  setCurrentEndpoint: (endpointName: string) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [currentEndpoint, setCurrentEndpoint] = useState<string>(() => {
    // Initialize from localStorage if available
    const savedEndpoint = localStorage.getItem('selectedEndpoint');
    return savedEndpoint || '';
  });
  const [chats, setChats] = useState<Chat[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(uuid());
  const [error, setError] = useState<string | null>(null);
  const chatsLoadedRef = useRef(false);

  const clearError = () => setError(null);

  useEffect(() => {
    const fetchChats = async () => {
      try {
        const chatHistory = await getChatHistory();
        setChats(chatHistory.sessions || []);
      } catch (error) {
        console.error('Failed to fetch chat history:', error);
        setError('Failed to load chat history. Please try again.');
      }
    };

    fetchChats();
  }, []);


  // Open the sidebar if there are chats, but only once
  useEffect(() => {
    if(chats.length > 0 && chatsLoadedRef.current === false) {
      chatsLoadedRef.current = true;
      setIsSidebarOpen(true)
    }
  }, [chats]);

  const sendMessage = async (content: string, includeHistory: boolean = true) => {
    if (!content.trim()) return;

    // Create new session if needed
    if (!currentSessionId) {
      startNewSession();
    }

    const userMessage: Message = { 
      message_id: uuid(),
      content, 
      role: 'user',
      timestamp: new Date()
    };

    const thinkingMessage: Message = {
      message_id: uuid(),
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      isThinking: true
    };

    setMessages(prev => [...prev, userMessage, thinkingMessage]);
    setLoading(true);
    setError(null);

    try {
      let accumulatedContent = '';
      let messageSources: any[] | null = null;
      let messageMetrics: { timeToFirstToken?: number; totalTime?: number } | null = null;
      let messageId = '';
      
      if (!currentSessionId) {
        throw new Error('No active session ID');
      }
      
      await apiSendMessage(content, currentSessionId, includeHistory, currentEndpoint, (chunk) => {
        console.log('🔄 CHATCONTEXT: Received chunk in callback:', chunk);
        
        if (chunk.content) {
          accumulatedContent = chunk.content;
          console.log('🔄 CHATCONTEXT: Updated accumulatedContent to:', accumulatedContent.substring(0, 100) + '...');
        }
        if (chunk.sources) {
          messageSources = chunk.sources;
        }
        if (chunk.metrics) {
          messageMetrics = chunk.metrics;
        }
        if (chunk.message_id) {
          messageId = chunk.message_id;
          console.log('🔄 CHATCONTEXT: Updated messageId to:', messageId);
        }
    
        console.log('🔄 CHATCONTEXT: Updating messages state with content:', chunk.content?.substring(0, 100) + '...');
        setMessages(prev => {
          const updated = prev.map(msg => 
            msg.message_id === thinkingMessage.message_id 
              ? { 
                  ...msg, 
                  content: chunk.content || '',
                  sources: chunk.sources,
                  metrics: chunk.metrics,
                  isThinking: false,
                  model: currentEndpoint
                }
              : msg
          );
          console.log('🔄 CHATCONTEXT: Updated messages:', updated);
          return updated;
        });
      });
      
      // TODO: The final message is now handled by the streaming callback
      // so we don't need to create a separate final message here
      console.log('🔄 CHATCONTEXT: Streaming completed, final accumulated content:', accumulatedContent.substring(0, 100) + '...');
      
      // const botMessage: Message = {
      //   message_id: messageId,
      //   content: accumulatedContent,
      //   role: 'assistant',
      //   timestamp: new Date(),
      //   isThinking: false,
      //   model: currentEndpoint,
      //   sources: messageSources,
      //   metrics: messageMetrics
      // };

      // setMessages(prev => prev.filter(msg => 
      //   msg.message_id !== thinkingMessage.message_id 
      // ).concat(botMessage));
      
    } catch (error) {
      console.error('Error sending message:', error);
      setError('Failed to send message. Please try again.');
      
      // Create error message with proper message_id
      const errorMessageId = uuid();
      const errorMessage: Message = { 
        message_id: errorMessageId,
        content: 'Sorry, I encountered an error. Please try again.',
        role: 'assistant',
        timestamp: new Date(),
        isThinking: false,
        model: currentEndpoint
      };
      
      // Keep the user message but update the thinking message to show error
      setMessages(prev => prev.map(msg => 
        msg.message_id === thinkingMessage.message_id 
          ? errorMessage
          : msg
      ));
    } finally {
      try {
        const historyResponse = await fetch(`${API_URL}/chats`);
        const historyData = await historyResponse.json();
        if (historyData.sessions) {
          setChats(historyData.sessions);
        }
      } catch (error) {
        console.error('Error fetching chat history:', error);
        setError('Failed to update chat history.');
      }
      setLoading(false);
    }
  };

  const selectChat = (sessionId: string) => {
    const selected = chats.find(chat => chat.sessionId === sessionId);
    
    if (selected) {
      setCurrentChat(selected);
      setCurrentSessionId(sessionId);
      
      const sessionMessages = chats
        .filter(chat => chat.sessionId === selected.sessionId)
        .flatMap(chat => chat.messages);
      
      setMessages(sessionMessages);
    }
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const startNewSession = () => {
    const newSessionId = uuid();
    setCurrentSessionId(newSessionId);
    setCurrentChat(null);
    setMessages([]);
  };

  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content)
      .then(() => {
        console.log('Message copied to clipboard');
      })
      .catch(err => {
        console.error('Failed to copy message:', err);
        setError('Failed to copy message to clipboard.');
      });
  };

  const logout = () => {
    // Clear local state
    setCurrentChat(null);
    setChats([]);
    setMessages([]);
    setCurrentSessionId(null);
    
    // Call the logout API endpoint which will handle the redirect
    apiLogout();
  };

  const handleSetCurrentEndpoint = (endpointName: string) => {
    setCurrentEndpoint(endpointName);
    localStorage.setItem('selectedEndpoint', endpointName);
  };

  return (
    <ChatContext.Provider value={{
      currentChat,
      chats,
      messages,
      loading,
      sendMessage,
      selectChat,
      isSidebarOpen,
      toggleSidebar,
      startNewSession,
      copyMessage,
      logout,
      error,
      clearError,
      currentEndpoint,
      setCurrentEndpoint: handleSetCurrentEndpoint
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}; 