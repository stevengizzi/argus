/**
 * Main application shell layout.
 *
 * Handles responsive layout:
 * - Desktop (≥1024px): Icon sidebar pinned left + main content
 * - Tablet (640–1023px): Bottom tab bar with labels
 * - Phone (<640px): Bottom tab bar with icons
 */

import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { useLiveStore } from '../stores/live';

interface AppShellProps {
  paperMode?: boolean;
}

export function AppShell({ paperMode = true }: AppShellProps) {
  const connect = useLiveStore((state) => state.connect);
  const disconnect = useLiveStore((state) => state.disconnect);

  // Auto-connect WebSocket when authenticated
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return (
    <div className="flex min-h-screen bg-argus-bg">
      {/* Desktop sidebar */}
      <Sidebar paperMode={paperMode} />

      {/* Main content area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-5 min-[1024px]:p-6 pb-20 min-[1024px]:pb-6">
        <Outlet />
      </main>

      {/* Mobile/tablet bottom navigation */}
      <MobileNav />
    </div>
  );
}
