/**
 * Auth store using Zustand.
 *
 * Manages authentication state with localStorage persistence.
 */

import { create } from 'zustand';
import { getToken, setToken, clearToken, login as apiLogin, refreshToken } from '../api/client';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  init: () => void;
  login: (password: string) => Promise<boolean>;
  logout: () => void;
  refresh: () => Promise<boolean>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  init: () => {
    const token = getToken();
    if (token) {
      set({ token, isAuthenticated: true });
      // Optionally refresh token on init
      get().refresh().catch(() => {
        // Token expired or invalid, clear it
        clearToken();
        set({ token: null, isAuthenticated: false });
      });
    }
  },

  login: async (password: string): Promise<boolean> => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiLogin(password);
      set({
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed';
      set({ isLoading: false, error: message });
      return false;
    }
  },

  logout: () => {
    clearToken();
    set({ token: null, isAuthenticated: false, error: null });
    // Redirect handled by clearToken or client.logout()
  },

  refresh: async (): Promise<boolean> => {
    try {
      const response = await refreshToken();
      setToken(response.access_token);
      set({ token: response.access_token, isAuthenticated: true });
      return true;
    } catch {
      return false;
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
