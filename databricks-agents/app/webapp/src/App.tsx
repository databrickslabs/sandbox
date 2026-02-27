import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ErrorBoundary from './components/common/ErrorBoundary'
import Layout from './components/layout/Layout'
import DiscoverPage from './pages/DiscoverPage'
import CollectionsPage from './pages/CollectionsPage'
import AgentsPage from './pages/AgentsPage'
import ChatPage from './pages/ChatPage'
import AgentChatPage from './pages/AgentChatPage'
import LineagePage from './pages/LineagePage'
import AuditLogPage from './pages/AuditLogPage'
import './App.css'

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/discover" replace />} />
            <Route path="discover" element={
              <ErrorBoundary><DiscoverPage /></ErrorBoundary>
            } />
            <Route path="collections" element={
              <ErrorBoundary><CollectionsPage /></ErrorBoundary>
            } />
            <Route path="agents" element={
              <ErrorBoundary><AgentsPage /></ErrorBoundary>
            } />
            <Route path="chat" element={
              <ErrorBoundary><ChatPage /></ErrorBoundary>
            } />
            <Route path="agent-chat" element={
              <ErrorBoundary><AgentChatPage /></ErrorBoundary>
            } />
            <Route path="lineage" element={
              <ErrorBoundary><LineagePage /></ErrorBoundary>
            } />
            <Route path="audit-log" element={
              <ErrorBoundary><AuditLogPage /></ErrorBoundary>
            } />
            <Route path="*" element={<Navigate to="/discover" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
