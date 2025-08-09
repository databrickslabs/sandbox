import React, { useRef, useEffect, useState } from 'react';
import styled from 'styled-components';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { useChat } from '../context/ChatContext';
import ChatTopNav from './ChatTopNav';

interface ChatContainerProps {
  'data-testid'?: string;
  sidebarOpen: boolean;
}

const ChatContainer = styled.div<ChatContainerProps>`
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100vh;
  margin-left: ${props => props.sidebarOpen ? '300px' : '100px'};
  width: ${props => props.sidebarOpen ? 'calc(100% - 300px)' : 'calc(100% - 100px)'};
  transition: margin-left 0.3s ease, width 0.3s ease;
  overflow: hidden;
`;

const ChatContent = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 0 16px;
  overflow-y: auto;
  height: calc(100vh - 48px); 
`;

const WelcomeContainer = styled.div<{ visible: boolean }>`
  display: ${props => props.visible ? 'flex' : 'none'};
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 50%;
  min-width: 300px;
  margin: auto;
  margin-bottom: 150px;
  padding: 24px 16px;
`;

const WelcomeMessage = styled.h1`
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin-bottom: 24px;
  text-align: center;
`;

const FixedInputWrapper = styled.div<{ visible: boolean }>`
  display: ${props => props.visible ? 'flex' : 'none'};
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 660px;
  margin: 2px auto;
  position: sticky;
  bottom: 20px;
  background-color: white;
  z-index: 10;
  box-shadow: 0 -10px 20px rgba(255, 255, 255, 0.9);
`;

const MessagesContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 650px;
  margin: 0 auto;
  max-width: 100%;
`;

const ChatArea: React.FC = () => {
  const { messages, isSidebarOpen } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [hasStartedChat, setHasStartedChat] = useState(false);
  const [includeHistory, setIncludeHistory] = useState(true);

  useEffect(() => {
    if (messages?.length > 0 && !hasStartedChat) {
      setHasStartedChat(true);
    } else if (messages?.length === 0 && hasStartedChat) {
      // Reset hasStartedChat when messages is cleared (new session)
      setHasStartedChat(false);
    }
  }, [messages, hasStartedChat]);
  
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [messages]);
  
  const hasMessages = messages?.length > 0 || hasStartedChat;
  
  return (
    <ChatContainer data-testid="chat-area" sidebarOpen={isSidebarOpen}>
      <ChatTopNav />
      <ChatContent data-testid="chat-content">
        <WelcomeContainer visible={!hasMessages} data-testid="welcome-container">
          <WelcomeMessage data-testid="welcome-message">What can I help with?</WelcomeMessage>
          <ChatInput 
            includeHistory={includeHistory}
            setIncludeHistory={setIncludeHistory}
            data-testid="chat-input" 
          />
        </WelcomeContainer>
        
        {hasMessages && (
          <MessagesContainer data-testid="messages-container" id="messages-container">
            {messages.map((message, index) => (
              <ChatMessage    
                key={message.message_id} 
                message={message}
                data-testid={`message-${index}`}
              />
            ))}
            {<div ref={messagesEndRef} />}
          </MessagesContainer>
        )}
      </ChatContent>
      
      <FixedInputWrapper visible={hasMessages} data-testid="fixed-input-wrapper">
        <ChatInput 
          fixed={true} 
          includeHistory={includeHistory}
          setIncludeHistory={setIncludeHistory}
        />
      </FixedInputWrapper>
    </ChatContainer>
  );
};

export default ChatArea; 