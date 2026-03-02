import { HashRouter, Routes, Route } from "react-router-dom";
import { AgentProvider } from "./hooks/useAgents";
import { Shell } from "./components/layout/Shell";
import { AgentGrid } from "./components/agents/AgentGrid";
import { AgentDetail } from "./components/detail/AgentDetail";
import { LineagePage } from "./pages/LineagePage";

export function App() {
  return (
    <AgentProvider>
      <HashRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<AgentGrid />} />
            <Route path="/agent/:name" element={<AgentDetail />} />
            <Route path="/lineage" element={<LineagePage />} />
          </Routes>
        </Shell>
      </HashRouter>
    </AgentProvider>
  );
}
