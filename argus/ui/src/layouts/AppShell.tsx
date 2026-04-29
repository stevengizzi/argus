/**
 * Main application shell layout.
 *
 * Handles responsive layout:
 * - Desktop (≥1024px): Icon sidebar pinned left + main content
 * - Tablet (640–1023px): Bottom tab bar with labels
 * - Phone (<640px): Bottom tab bar with icons
 *
 * Mounts global panels: SymbolDetailPanel, CopilotPanel, CopilotButton.
 */

import { useEffect, useCallback, useRef } from 'react';
import { useLocation, useOutlet, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { useLiveStore } from '../stores/live';
import { useCopilotUIStore } from '../stores/copilotUI';
import { SymbolDetailPanel } from '../features/symbol';
import { CopilotPanel, CopilotButton } from '../features/copilot';
import { AlertBanner } from '../components/AlertBanner';
import { AlertToastStack } from '../components/AlertToast';
import { pageVariants } from '../utils/motion';

interface AppShellProps {
  paperMode?: boolean;
}

// Module-level cache to store outlet elements by pathname.
// This persists across re-renders and prevents content flash during transitions.
const outletCache = new Map<string, React.ReactNode>();

// Navigation routes for keyboard shortcuts (1–9 and 0)
const NAV_ROUTES = [
  '/',           // 1 = Dashboard
  '/trades',     // 2 = Trades
  '/performance',// 3 = Performance
  '/arena',      // 4 = The Arena
  '/orchestrator',// 5 = Orchestrator
  '/observatory',// 6 = Observatory
  '/patterns',   // 7 = Pattern Library
  '/debrief',    // 8 = The Debrief
  '/system',     // 9 = System
  '/experiments',// 0 = Experiments
];

export function AppShell({ paperMode = true }: AppShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const currentOutlet = useOutlet();
  const connect = useLiveStore((state) => state.connect);
  const disconnect = useLiveStore((state) => state.disconnect);
  const toggleCopilot = useCopilotUIStore((state) => state.toggle);
  const mainRef = useRef<HTMLElement>(null);

  // Cache the current outlet element by its pathname.
  // When AnimatePresence clones the exiting element, retrieving from cache
  // returns the correct (old) content instead of the new route's content.
  outletCache.set(location.pathname, currentOutlet);

  // Auto-connect WebSocket when authenticated
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Global keyboard shortcuts for mobile (Sidebar handles desktop but mobile needs this)
  // 1-9 and 0 for navigation, Cmd/Ctrl+K for copilot
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        // Exception: Cmd/Ctrl+K should work even in inputs (common pattern)
        if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
          e.preventDefault();
          toggleCopilot();
        }
        return;
      }

      // Cmd/Ctrl+K for copilot toggle (works globally)
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        toggleCopilot();
        return;
      }

      // Ignore single-key shortcuts if any modifier is held
      const hasModifier = e.metaKey || e.ctrlKey || e.altKey || e.shiftKey;
      if (hasModifier) {
        return;
      }

      // Numeric shortcuts for navigation (1–9, 0)
      const keyNum = parseInt(e.key, 10);
      if (!isNaN(keyNum) && keyNum >= 0 && keyNum <= 9) {
        const routeIndex = keyNum === 0 ? 9 : keyNum - 1;
        if (routeIndex < NAV_ROUTES.length) {
          navigate(NAV_ROUTES[routeIndex]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate, toggleCopilot]);

  // Clean up old cache entries and scroll to top after exit transition completes.
  // This creates the effect: fade to black at old scroll position → scroll to top → fade in new page.
  const handleExitComplete = useCallback(() => {
    // Scroll to top instantly between exit and enter animations
    mainRef.current?.scrollTo(0, 0);

    // Keep only current pathname in cache
    for (const key of outletCache.keys()) {
      if (key !== location.pathname) {
        outletCache.delete(key);
      }
    }
  }, [location.pathname]);

  return (
    <div className="flex h-dvh bg-argus-bg overflow-hidden">
      {/* Cross-page alert observability mounts (Sprint 31.91 Session 5e — D13).
          Banner sits sticky at the top of the visible area; toast is fixed-
          positioned and lives outside flex flow. Both visible on every page. */}
      <div className="absolute top-0 left-0 right-0 z-40 px-4 pt-2 min-[1024px]:left-16">
        <AlertBanner />
      </div>
      <AlertToastStack />

      {/* Desktop sidebar */}
      <Sidebar paperMode={paperMode} />

      {/* Main content area — offset for fixed sidebar on desktop, extra pb for mobile nav */}
      {/* min-w-0 breaks flexbox min-content propagation, overflow-x-hidden prevents horizontal scroll */}
      <main
        ref={mainRef}
        className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden p-4 md:p-5 min-[1024px]:p-6 pb-24 min-[1024px]:pb-6 min-[1024px]:ml-16 min-[1024px]:pt-6"
      >
        {/* Safe area spacer for PWA/iOS — adds to, not replaces, base padding */}
        <div className="safe-top min-[1024px]:hidden" />
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

      {/* Global panels */}
      <SymbolDetailPanel />
      <CopilotPanel />
      <CopilotButton />
    </div>
  );
}
