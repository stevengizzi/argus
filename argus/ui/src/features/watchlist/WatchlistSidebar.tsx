/**
 * WatchlistSidebar - Collapsible sidebar showing scanner candidates.
 *
 * Responsive layout:
 * - Desktop (>=1024px): 280px right sidebar, collapsible
 * - Tablet (640-1023px): Slide-out panel from right edge
 * - Mobile (<640px): Full-screen overlay accessed via toolbar button
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronLeft, X, List, TrendingUp } from 'lucide-react';
import { useWatchlist } from '../../hooks/useWatchlist';
import { useWatchlistUIStore } from '../../stores/watchlistUI';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { Skeleton } from '../../components/Skeleton';
import { WatchlistItem } from './WatchlistItem';
import type { WatchlistItem as WatchlistItemType } from '../../api/types';

const SIDEBAR_WIDTH = 280;

interface WatchlistSidebarProps {
  className?: string;
}

export function WatchlistSidebar({ className = '' }: WatchlistSidebarProps) {
  const { data, isLoading } = useWatchlist();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const isMobile = useMediaQuery('(max-width: 639px)');

  const isCollapsed = useWatchlistUIStore((s) => s.isCollapsed);
  const toggleCollapsed = useWatchlistUIStore((s) => s.toggleCollapsed);
  const isMobileOpen = useWatchlistUIStore((s) => s.isMobileOpen);
  const setMobileOpen = useWatchlistUIStore((s) => s.setMobileOpen);

  // Close mobile overlay when switching to desktop
  useEffect(() => {
    if (isDesktop && isMobileOpen) {
      setMobileOpen(false);
    }
  }, [isDesktop, isMobileOpen, setMobileOpen]);

  const symbols = data?.symbols ?? [];

  // Desktop: Inline sidebar
  if (isDesktop) {
    return (
      <aside
        className={`relative flex flex-col bg-argus-surface border-l border-argus-border transition-all duration-300 ${className}`}
        style={{ width: isCollapsed ? 48 : SIDEBAR_WIDTH }}
      >
        {/* Collapse toggle button */}
        <button
          onClick={toggleCollapsed}
          className="absolute -left-3 top-4 z-10 w-6 h-6 bg-argus-surface-2 border border-argus-border rounded-full flex items-center justify-center hover:bg-argus-surface-3 transition-colors"
          aria-label={isCollapsed ? 'Expand watchlist' : 'Collapse watchlist'}
        >
          {isCollapsed ? (
            <ChevronLeft className="w-4 h-4 text-argus-text-dim" />
          ) : (
            <ChevronRight className="w-4 h-4 text-argus-text-dim" />
          )}
        </button>

        {isCollapsed ? (
          // Collapsed state: show icon only
          <div className="flex flex-col items-center pt-12">
            <List className="w-5 h-5 text-argus-text-dim" />
            <span className="mt-2 text-xs text-argus-text-dim [writing-mode:vertical-rl] rotate-180">
              Watchlist
            </span>
          </div>
        ) : (
          // Expanded state: full content
          <WatchlistContent
            symbols={symbols}
            isLoading={isLoading}
          />
        )}
      </aside>
    );
  }

  // Tablet/Mobile: Overlay/slide-out panel
  return (
    <>
      {/* Toggle button for mobile/tablet */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed bottom-20 right-4 z-40 w-12 h-12 bg-argus-accent rounded-full flex items-center justify-center shadow-lg hover:bg-argus-accent/90 transition-colors min-[1024px]:hidden"
        aria-label="Open watchlist"
      >
        <List className="w-6 h-6 text-white" />
      </button>

      {/* Overlay/Panel */}
      <AnimatePresence>
        {isMobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/50 z-50 min-[1024px]:hidden"
              onClick={() => setMobileOpen(false)}
            />

            {/* Panel */}
            <motion.aside
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className={`fixed top-0 right-0 bottom-0 z-50 bg-argus-surface border-l border-argus-border flex flex-col min-[1024px]:hidden ${
                isMobile ? 'w-full' : 'w-80'
              }`}
            >
              {/* Header with close button */}
              <div className="flex items-center justify-between p-4 border-b border-argus-border safe-top">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-argus-accent" />
                  <h2 className="text-lg font-semibold text-argus-text">Watchlist</h2>
                  <span className="text-sm text-argus-text-dim">({symbols.length})</span>
                </div>
                <button
                  onClick={() => setMobileOpen(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-argus-surface-2 transition-colors"
                  aria-label="Close watchlist"
                >
                  <X className="w-5 h-5 text-argus-text-dim" />
                </button>
              </div>

              <WatchlistContent
                symbols={symbols}
                isLoading={isLoading}
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

interface WatchlistContentProps {
  symbols: WatchlistItemType[];
  isLoading: boolean;
}

function WatchlistContent({ symbols, isLoading }: WatchlistContentProps) {
  if (isLoading) {
    return (
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="flex items-center gap-2 px-1 pb-2 border-b border-argus-border">
          <Skeleton width={20} height={20} variant="circle" />
          <Skeleton width={80} height={20} />
          <Skeleton width={40} height={16} className="ml-auto" />
        </div>
        {[...Array(6)].map((_, i) => (
          <WatchlistItemSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (symbols.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-4 text-center">
        <TrendingUp className="w-10 h-10 text-argus-text-dim mb-3" />
        <p className="text-sm text-argus-text-dim">No symbols on watchlist</p>
        <p className="text-xs text-argus-text-dim mt-1">
          Scanner candidates will appear here
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-argus-border">
        <TrendingUp className="w-4 h-4 text-argus-accent" />
        <span className="text-sm font-medium text-argus-text">Watchlist</span>
        <span className="text-xs text-argus-text-dim">({symbols.length})</span>
      </div>

      {/* Symbol list */}
      <div className="flex-1 overflow-y-auto">
        {symbols.map((item) => (
          <WatchlistItem key={item.symbol} item={item} />
        ))}
      </div>
    </>
  );
}

function WatchlistItemSkeleton() {
  return (
    <div className="p-2 border-b border-argus-border/50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Skeleton width={48} height={16} />
          <Skeleton width={60} height={14} />
        </div>
        <Skeleton width={32} height={16} />
      </div>
      <Skeleton width="100%" height={20} className="mb-2" />
      <div className="flex gap-1">
        <Skeleton width={32} height={16} />
        <Skeleton width={32} height={16} />
      </div>
    </div>
  );
}
