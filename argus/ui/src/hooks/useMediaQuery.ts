/**
 * Hook for responsive media query detection.
 *
 * Returns true if the viewport matches the given media query.
 * Updates on resize.
 */

import { useSyncExternalStore } from 'react';

function getServerSnapshot(): boolean {
  return false;
}

export function useMediaQuery(query: string): boolean {
  // Use useSyncExternalStore for proper subscription pattern
  const subscribe = (callback: () => void) => {
    const mediaQuery = window.matchMedia(query);
    mediaQuery.addEventListener('change', callback);
    return () => mediaQuery.removeEventListener('change', callback);
  };

  const getSnapshot = () => {
    return window.matchMedia(query).matches;
  };

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/**
 * Returns true if the viewport is at least the given Tailwind breakpoint.
 * Useful for responsive stagger animations.
 */
export function useIsMultiColumn(): boolean {
  // md breakpoint (640px) is when grids go from 1 column to 2+
  return useMediaQuery('(min-width: 640px)');
}
