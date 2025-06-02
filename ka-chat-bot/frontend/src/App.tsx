import React from 'react';
import styled from 'styled-components';
import { ChatProvider } from './context/ChatContext';
import LeftComponent from './components/LeftComponent';
import ChatArea from './components/ChatArea';

// Define the props type explicitly
interface AppContainerProps {
  'data-testid'?: string;
}

interface MainContentProps {
  'data-testid'?: string;
}

const AppContainer = styled.div<AppContainerProps>`
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  overflow: hidden;
`;

const MainContent = styled.div<MainContentProps>`
  display: flex;
  height: 100vh;
  width: 100%;
  position: fixed;
`;

const App: React.FC = () => {
  return (
    <ChatProvider>
      <AppContainer data-testid="app-container">
        <MainContent data-testid="main-content">
          <LeftComponent />
          <ChatArea />
        </MainContent>
      </AppContainer>
    </ChatProvider>
  );
};

export default App;
