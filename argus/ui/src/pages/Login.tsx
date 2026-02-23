/**
 * Login page component.
 *
 * Dark-themed login form for single-user authentication.
 */

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/auth';
import { Eye, EyeOff, Lock } from 'lucide-react';

export function Login() {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login, isLoading, error, clearError } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  // Get redirect destination from state or default to home
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    const success = await login(password);
    if (success) {
      navigate(from, { replace: true });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-argus-bg p-4">
      <div className="w-full max-w-md">
        {/* Logo / Title */}
        <div className="text-center mb-8">
          <img
            src="/argus-logo-login.png"
            alt="ARGUS"
            width={80}
            height={80}
            className="mx-auto mb-4"
          />
          <h1 className="text-3xl font-bold text-argus-text mb-2">ARGUS</h1>
          <p className="text-argus-text-dim">Command Center</p>
        </div>

        {/* Login Card */}
        <div className="bg-argus-surface border border-argus-border rounded-lg p-6 shadow-lg">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Password field */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-argus-text-dim mb-2"
              >
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-argus-text-dim" />
                </div>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-10 py-2.5 bg-argus-bg border border-argus-border rounded-lg text-argus-text placeholder-argus-text-dim focus:outline-none focus:ring-2 focus:ring-argus-accent focus:border-transparent"
                  placeholder="Enter password"
                  required
                  autoComplete="current-password"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-argus-text-dim hover:text-argus-text"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="bg-red-900/20 border border-red-800 text-argus-danger rounded-lg p-3 text-sm">
                {error}
              </div>
            )}

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading || !password}
              className="w-full py-2.5 px-4 bg-argus-accent hover:bg-blue-600 disabled:bg-argus-accent/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-argus-accent focus:ring-offset-2 focus:ring-offset-argus-bg"
            >
              {isLoading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-argus-text-dim text-sm mt-6">
          Argus Trading System
        </p>
      </div>
    </div>
  );
}
