/**
 * Hook for registering page-specific context with the AI Copilot.
 *
 * Each page calls this hook to provide context data that is sent along
 * with user messages to the Copilot. Context is lazily evaluated — the
 * provider function is only called when sending a message.
 *
 * Sprint 22, Session 4b.
 */

import { useEffect, useCallback, useRef } from 'react';
import { useCopilotUIStore } from '../stores/copilotUI';

/**
 * Register page-specific context with the Copilot.
 *
 * @param page - Page identifier (e.g., 'Dashboard', 'Trades')
 * @param contextData - Function that returns current context data (called lazily)
 * @returns Object with the current page name
 *
 * @example
 * ```tsx
 * const { page } = useCopilotContext('Dashboard', () => ({
 *   equity: portfolio.equity,
 *   dailyPnl: portfolio.dailyPnl,
 *   positionsCount: positions.length,
 * }));
 * ```
 */
export function useCopilotContext(
  page: string,
  contextData: () => Record<string, unknown>
): { page: string } {
  const registerContextProvider = useCopilotUIStore((state) => state.registerContextProvider);
  const unregisterContextProvider = useCopilotUIStore((state) => state.unregisterContextProvider);

  // Use ref to always have the latest contextData without re-registering
  const contextDataRef = useRef(contextData);
  contextDataRef.current = contextData;

  // Stable callback that reads from the ref
  const stableContextProvider = useCallback(() => {
    return contextDataRef.current();
  }, []);

  useEffect(() => {
    // Register this page's context provider
    registerContextProvider(page, stableContextProvider);

    // Cleanup: unregister when unmounting or page changes
    return () => {
      unregisterContextProvider(page);
    };
  }, [page, stableContextProvider, registerContextProvider, unregisterContextProvider]);

  return { page };
}
