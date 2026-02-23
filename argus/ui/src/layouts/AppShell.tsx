/**
 * Main application shell layout.
 *
 * Handles responsive layout:
 * - Desktop (≥1024px): Icon sidebar pinned left + main content
 * - Tablet (640–1023px): Bottom tab bar with labels
 * - Phone (<640px): Bottom tab bar with icons
 */

import { useEffect, useCallback } from 'react';
import { useLocation, useOutlet } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { useLiveStore } from '../stores/live';
import { pageVariants } from '../utils/motion';

interface AppShellProps {
  paperMode?: boolean;
}

// Module-level cache to store outlet elements by pathname.
// This persists across re-renders and prevents content flash during transitions.
const outletCache = new Map<string, React.ReactNode>();

export function AppShell({ paperMode = true }: AppShellProps) {
  const location = useLocation();
  const currentOutlet = useOutlet();
  const connect = useLiveStore((state) => state.connect);
  const disconnect = useLiveStore((state) => state.disconnect);

  // Cache the current outlet element by its pathname.
  // When AnimatePresence clones the exiting element, retrieving from cache
  // returns the correct (old) content instead of the new route's content.
  outletCache.set(location.pathname, currentOutlet);

  // Auto-connect WebSocket when authenticated
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Clean up old cache entries after transition to prevent memory leak
  const handleExitComplete = useCallback(() => {
    // Keep only current pathname in cache
    for (const key of outletCache.keys()) {
      if (key !== location.pathname) {
        outletCache.delete(key);
      }
    }
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-argus-bg">
      {/* Desktop sidebar */}
      <Sidebar paperMode={paperMode} />

      {/* Main content area — offset for fixed sidebar on desktop, extra pb for mobile nav */}
      {/* min-w-0 breaks flexbox min-content propagation, overflow-x-hidden prevents horizontal scroll */}
      <main className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden p-4 md:p-5 min-[1024px]:p-6 pb-24 min-[1024px]:pb-6 min-[1024px]:ml-16">
        <AnimatePresence mode="wait" onExitComplete={handleExitComplete}>
          <motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            {outletCache.get(location.pathname)}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Mobile/tablet bottom navigation */}
      <MobileNav />
    </div>
  );
}
