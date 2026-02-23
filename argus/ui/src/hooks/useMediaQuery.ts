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

/**
 * Returns one of three height values based on viewport width.
 * Reacts to viewport changes (e.g., device rotation).
 *
 * @param desktop - Height for desktop (>=1024px)
 * @param tablet - Height for tablet (640-1023px)
 * @param mobile - Height for mobile (<640px)
 */
export function useResponsiveHeight(desktop: number, tablet: number, mobile: number): number {
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const isTablet = useMediaQuery('(min-width: 640px)');
  if (isDesktop) return desktop;
  if (isTablet) return tablet;
  return mobile;
}
