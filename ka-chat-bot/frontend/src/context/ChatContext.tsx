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
  selectChat: (chatId: string) => Promise<void>;
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

    // Clear any leftover thinking states from previous messages, then add new messages
    setMessages(prev => [
      ...prev.map(msg => msg.isThinking ? { ...msg, isThinking: false } : msg),
      userMessage, 
      thinkingMessage
    ]);
    setLoading(true);
    setError(null);

    try {
      if (!currentSessionId) {
        throw new Error('No active session ID');
      }
      
      await apiSendMessage(content, currentSessionId, includeHistory, currentEndpoint, (chunk) => {
        
        // Only set isThinking to false when we receive the completion message
        const isComplete = chunk.isComplete || false;
        
        setMessages(prev => {
          const updated = prev.map((msg, index) => {
            // Only update the last message if it's the thinking message
            if (index === prev.length - 1 && msg.message_id === thinkingMessage.message_id && msg.role === 'assistant') {
              return { 
                ...msg, 
                content: chunk.content || '',
                sources: chunk.sources,
                metrics: chunk.metrics,
                isThinking: !isComplete, // Keep thinking until completion
                model: currentEndpoint
              };
            }
            return msg;
          });
          return updated;
        });
      });
      
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
      // Update sidebar with latest chat sessions after a delay
      setTimeout(async () => {
        try {
          const historyResponse = await fetch(`${API_URL}/chats`);
          const historyData = await historyResponse.json();
          if (historyData.sessions) {
            setChats(historyData.sessions);
          }
        } catch (error) {
          console.error('Error fetching chat history for sidebar:', error);
        }
      }, 200); // 200ms delay to let database write complete
      
      setLoading(false);
    }
  };

  const selectChat = async (sessionId: string) => {
    const selected = chats.find(chat => chat.sessionId === sessionId);
    
    if (selected) {
      setCurrentChat(selected);
      setCurrentSessionId(sessionId);
      
      // If selecting the current session, keep current messages as they're more up-to-date
      if (sessionId === currentSessionId) {
        return;
      }
      
      // For other sessions, fetch fresh chat history to ensure we have latest messages
      try {
        const historyResponse = await fetch(`${API_URL}/chats`);
        const historyData = await historyResponse.json();
        if (historyData.sessions) {
          setChats(historyData.sessions);
          
          // Find the updated session data
          const updatedSelected = historyData.sessions.find((chat: any) => chat.sessionId === sessionId);
          if (updatedSelected) {
            setMessages(updatedSelected.messages);
          } else {
            setMessages(selected.messages); // fallback to cached data
          }
        } else {
          setMessages(selected.messages); // fallback to cached data
        }
      } catch (error) {
        console.error('Error fetching fresh chat history:', error);
        setMessages(selected.messages); // fallback to cached data
      }
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