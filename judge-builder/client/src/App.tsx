import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import WelcomePage from "./pages/WelcomePage"
import JudgeDetailPage from "./pages/JudgeDetailPage"
import { Toaster } from "./components/ui/toaster"
import { ToastProvider } from "./contexts/ToastContext"

function App() {
  return (
    <ToastProvider>
      <Router>
        <div className="min-h-screen bg-background">
          <Routes>
            <Route path="/" element={<WelcomePage />} />
            <Route path="/judge/:judgeId" element={<JudgeDetailPage />} />
          </Routes>
          <Toaster />
        </div>
      </Router>
    </ToastProvider>
  )
}

export default App