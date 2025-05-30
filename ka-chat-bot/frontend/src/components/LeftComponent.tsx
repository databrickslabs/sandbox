import React from 'react';
import styled from 'styled-components';
import { useChat } from '../context/ChatContext';
import menuIconUrl from '../assets/images/menu_icon.svg';
import newChatIconUrl from '../assets/images/newchat_icon.svg';
import Sidebar from './Sidebar';

interface LeftComponentProps {
  'data-testid'?: string;
}

interface LeftContainerProps {
  isOpen: boolean;
  'data-testid'?: string;
}

interface NewChatButtonProps {
  isSidebarOpen: boolean;
}

const LeftContainer = styled.div<LeftContainerProps>`
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 10;
  height: 100vh;
  width: ${props => props.isOpen ? '300px' : '0px'};
  border-right: ${props => props.isOpen ? '1px solid #DCDCDC' : 'none'};
  transition: width 0.2s ease;
`;

const NavLeft = styled.div`
  display: flex;
  align-items: center;
  height: 48px;
  padding: 10 16px 0 20px;
  gap: 16px;
  justify-content: space-between;
`;

const MenuButton = styled.button`
  min-width: 32px;
  height: 32px;
  border: none;
  background-color: transparent;
  background-image: url(${menuIconUrl});
  background-repeat: no-repeat;
  background-position: center;
  cursor: pointer;
  border-radius: 4px;
  margin: 0;
  padding: 0;
  flex-shrink: 0;
  
  &:hover {
    background-color: rgba(34, 114, 180, 0.08);
    color: #0E538B;
  }
`;

const NewChatButton = styled.button<NewChatButtonProps>`
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: 10px;
  padding: 6px 12px;
  border: ${props => props.isSidebarOpen ? '1px solid #C0CDD8' : 'none'};
  border-radius: 4px;
  background-color: transparent;
  color: #11171C;
  font-size: 15px;
  cursor: pointer;
  box-shadow: ${props => props.isSidebarOpen ? '0px 1px 0px rgba(0, 0, 0, 0.05)' : 'none'};
  height: 32px;
  &:hover {
    background-color: rgba(34, 114, 180, 0.08);
    color: #0E538B;
  }
`;
const NewChatIcon = styled.div`
  width: 16px;
  height: 16px;
  background-image: url(${newChatIconUrl});
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
`;


const LeftComponent: React.FC<LeftComponentProps> = () => {
  const { isSidebarOpen, toggleSidebar, startNewSession } = useChat();
  const handleNewChat = () => {
    startNewSession();
  };
  
  return (
    <LeftContainer isOpen={isSidebarOpen} data-testid="left-component">
      <NavLeft data-testid="nav-left">
        <MenuButton onClick={toggleSidebar} data-testid="menu-button"/>
        {isSidebarOpen ? (
          <NewChatButton onClick={handleNewChat} data-testid="nav-new-chat-button" isSidebarOpen={isSidebarOpen}>
            <NewChatIcon />
            <span>New chat</span>
          </NewChatButton>
        ) : (
          <NewChatButton onClick={handleNewChat} data-testid="nav-new-chat-button" isSidebarOpen={isSidebarOpen}>
            <NewChatIcon />
          </NewChatButton>
        )}
      </NavLeft>
      <Sidebar />
    </LeftContainer>
  );
};

export default LeftComponent; 