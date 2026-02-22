/**
 * Main App component with routing.
 */

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/auth';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
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

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <ConnectionTest />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dev/connection"
          element={
            <ProtectedRoute>
              <ConnectionTest />
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
