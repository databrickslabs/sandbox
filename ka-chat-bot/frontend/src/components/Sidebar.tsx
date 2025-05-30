import React, { useMemo } from 'react';
import styled from 'styled-components';
import { useChat } from '../context/ChatContext';
import { Chat } from '../types';

interface SidebarContainerProps {
  isOpen: boolean;
  'data-testid'?: string;
}

const SidebarContainer = styled.div<SidebarContainerProps>`
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px);
  width: 100%;
  overflow: ${props => props.isOpen ? 'visible' : 'hidden'};
  padding: ${props => props.isOpen ? '8px 16px 24px 16px' : '0'};
  white-space: nowrap;
`;

const SidebarHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  margin-bottom: 8px;

`;

const SidebarHeaderText = styled.div`
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const InfoIcon = styled.div`
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background-color: #5F7281;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  cursor: help;
  position: relative;

  &:hover::after {
    content: "Chat history is temporary and will be cleared periodically";
    position: absolute;
    left: 24px;
    top: 50%;
    transform: translateY(-50%);
    background-color: #11171C;
    color: white;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 14px;
    white-space: nowrap;
    z-index: 1000;
  }
`;

const ChatList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  max-height: calc(100vh - 120px); /* Adjust for header/footer height */
`;

const SessionGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const ChatItem = styled.div<{ active: boolean }>`
  padding: 6px 12px;
  cursor: pointer;
  font-size: 15px;
  color: ${props => props.active ? '#0E538B' : '#11171C'};
  background-color: ${props => props.active ? 'rgba(34, 114, 180, 0.08)' : 'transparent'};
  border-radius: 4px;
  height: 32px;
  display: flex;
  align-items: center;
  margin-bottom: 0;
  box-shadow: none;
  position: relative;
  overflow: hidden;
  white-space: nowrap;

  
  &:hover {
    background-color: rgba(34, 114, 180, 0.08);
  }
`;

const ChatItemText = styled.span`
  position: relative;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  flex: 1;
`;

const DateHeader = styled.div`
  font-size: 15px;
  font-weight: 600;
  color: #5F7281;
  padding: 16px 12px 8px 12px;
`;

const Sidebar: React.FC = () => {
  const { chats, currentChat, selectChat, isSidebarOpen } = useChat();

  // Group chats by date categories and sessions
  const groupedChats = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    // First group by date category
    const dateGroups: { [key: string]: { [key: string]: Chat[] } } = {
      'Today': {},
      'Yesterday': {},
      'Previous 7 days': {},
      'Older': {}
    };

    chats.forEach(chat => {
      let chatDate = new Date(chat.timestamp);
      if (isNaN(chatDate.getTime())) {
        chatDate = new Date();
      }
      chatDate.setHours(0, 0, 0, 0);
      
      let dateCategory: string;
      if (chatDate.getTime() === today.getTime()) {
        dateCategory = 'Today';
      } else if (chatDate.getTime() === yesterday.getTime()) {
        dateCategory = 'Yesterday';
      } else if (chatDate >= lastWeek) {
        dateCategory = 'Previous 7 days';
      } else {
        dateCategory = 'Older';
      }

      // Then group by session within each date category
      if (!dateGroups[dateCategory][chat.sessionId]) {
        dateGroups[dateCategory][chat.sessionId] = [];
      }
      dateGroups[dateCategory][chat.sessionId].push(chat);
    });

    return dateGroups;
  }, [chats]);

  return (
    <SidebarContainer isOpen={isSidebarOpen} data-testid="sidebar">
      <SidebarHeader data-testid="sidebar-header">
        <SidebarHeaderText>
          Recent chats
          <InfoIcon data-testid="info-tooltip">i</InfoIcon>
        </SidebarHeaderText>
      </SidebarHeader>
      
      <ChatList data-testid="chat-list">
        {Object.entries(groupedChats).map(([dateCategory, sessions]) => {
          // Only show date categories that have chats
          if (Object.keys(sessions).length === 0) return null;

          return (
            <div key={dateCategory}>
              <DateHeader>{dateCategory}</DateHeader>
              {Object.entries(sessions).map(([sessionId, sessionChats]) => (
                <SessionGroup key={sessionId} data-testid={`session-group-${sessionId}`}>
                  <ChatItem
                    active={currentChat?.sessionId === sessionId}
                    onClick={() => selectChat(sessionChats[0].sessionId)}
                    data-testid={`chat-item-${sessionChats[0].sessionId}`}
                  >
                    <ChatItemText>{sessionChats[0].firstQuery}</ChatItemText>
                  </ChatItem>
                </SessionGroup>
              ))}
            </div>
          );
        })}
      </ChatList>
    </SidebarContainer>
  );
};

export default Sidebar; 