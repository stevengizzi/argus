/**
 * Main App component with routing.
 */

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/auth';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppShell } from './layouts/AppShell';
import { Login } from './pages/Login';
import { DashboardPage } from './pages/DashboardPage';
import { TradesPage } from './pages/TradesPage';
import { PerformancePage } from './pages/PerformancePage';
import { PatternLibraryPage } from './pages/PatternLibraryPage';
import { OrchestratorPage } from './pages/OrchestratorPage';
import { DebriefPage } from './pages/DebriefPage';
import { SystemPage } from './pages/SystemPage';
import { ConnectionTest } from './pages/ConnectionTest';

function App() {
  const init = useAuthStore((state) => state.init);

  // Initialize auth state from localStorage on mount
  useEffect(() => {
    init();
  }, [init]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected routes with AppShell layout */}
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="trades" element={<TradesPage />} />
          <Route path="performance" element={<PerformancePage />} />
          <Route path="patterns" element={<PatternLibraryPage />} />
          <Route path="orchestrator" element={<OrchestratorPage />} />
          <Route path="debrief" element={<DebriefPage />} />
          <Route path="system" element={<SystemPage />} />
          <Route path="dev/connection" element={<ConnectionTest />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
