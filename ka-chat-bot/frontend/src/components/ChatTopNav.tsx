import React from 'react';
import styled from 'styled-components';
import UserMenu from './UserMenu';

const TopNav = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  height: 56px;
`;

const ChatTopNav: React.FC = () => {
  return (
    <TopNav data-testid="chat-top-nav">
      <UserMenu />
    </TopNav>
  );
};

export default ChatTopNav; 