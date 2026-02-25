/**
 * WatchlistSidebar - Collapsible sidebar showing scanner candidates.
 *
 * Responsive layout:
 * - Desktop (>=1024px): 280px right sidebar, collapsible
 * - Tablet (640-1023px): Slide-out panel from right edge
 * - Mobile (<640px): Full-screen overlay accessed via toolbar button
 *
 * Sprint 19, Session 11 enhancements:
 * - Sort controls (Gap %, Strategy count, VWAP State)
 * - FAB count badge on mobile/tablet
 * - Header with scan timestamp
 * - Click-through to Trade Detail panel
 */

import { useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronLeft, X, List, TrendingUp, ChevronDown } from 'lucide-react';
import { useWatchlist } from '../../hooks/useWatchlist';
import { useWatchlistUIStore, type WatchlistSortMode } from '../../stores/watchlistUI';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { Skeleton } from '../../components/Skeleton';
import { WatchlistItem } from './WatchlistItem';
import type { WatchlistItem as WatchlistItemType, VwapState } from '../../api/types';

const SIDEBAR_WIDTH = 280;

// VWAP state priority for sorting
const vwapStatePriority: Record<VwapState, number> = {
  entered: 0,
  below_vwap: 1,
  above_vwap: 2,
  watching: 3,
};

interface WatchlistSidebarProps {
  className?: string;
  onSymbolClick?: (symbol: string) => void;
}

export function WatchlistSidebar({ className = '', onSymbolClick }: WatchlistSidebarProps) {
  const { data, isLoading } = useWatchlist();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const isMobile = useMediaQuery('(max-width: 639px)');

  const isCollapsed = useWatchlistUIStore((s) => s.isCollapsed);
  const toggleCollapsed = useWatchlistUIStore((s) => s.toggleCollapsed);
  const isMobileOpen = useWatchlistUIStore((s) => s.isMobileOpen);
  const setMobileOpen = useWatchlistUIStore((s) => s.setMobileOpen);
  const sortMode = useWatchlistUIStore((s) => s.sortMode);

  // Close mobile overlay when switching to desktop
  useEffect(() => {
    if (isDesktop && isMobileOpen) {
      setMobileOpen(false);
    }
  }, [isDesktop, isMobileOpen, setMobileOpen]);

  const symbols = data?.symbols ?? [];

  // Sort symbols based on current sort mode
  const sortedSymbols = useMemo(() => {
    if (symbols.length === 0) return symbols;

    return [...symbols].sort((a, b) => {
      switch (sortMode) {
        case 'gap':
          // Descending by gap_pct (highest gap first)
          return b.gap_pct - a.gap_pct;
        case 'strategy':
          // Descending by number of strategies watching
          return b.strategies.length - a.strategies.length;
        case 'state':
          // By VWAP state priority (entered first, then below, above, watching)
          return vwapStatePriority[a.vwap_state] - vwapStatePriority[b.vwap_state];
        default:
          return 0;
      }
    });
  }, [symbols, sortMode]);

  // Desktop: Inline sidebar
  if (isDesktop) {
    return (
      <aside
        className={`relative flex flex-col bg-argus-surface border-l border-argus-border transition-all duration-300 ${className}`}
        style={{ width: isCollapsed ? 48 : SIDEBAR_WIDTH }}
      >
        {/* Collapse toggle button - outside overflow-hidden area */}
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

        {/* Content area with overflow hidden for clean transitions */}
        <div className="flex-1 overflow-hidden">
          <AnimatePresence mode="wait">
            {isCollapsed ? (
              <motion.div
                key="collapsed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex flex-col items-center pt-12"
              >
                <List className="w-5 h-5 text-argus-text-dim" />
                <span className="mt-2 text-xs text-argus-text-dim [writing-mode:vertical-rl] rotate-180">
                  Watchlist
                </span>
              </motion.div>
            ) : (
              <motion.div
                key="expanded"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex flex-col h-full"
              >
                <WatchlistContent
                  symbols={sortedSymbols}
                  isLoading={isLoading}
                  onSymbolClick={onSymbolClick}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </aside>
    );
  }

  // Tablet/Mobile: Overlay/slide-out panel
  return (
    <>
      {/* Toggle button for mobile/tablet with count badge */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed bottom-20 right-4 z-40 w-12 h-12 bg-argus-accent rounded-full flex items-center justify-center shadow-lg hover:bg-argus-accent/90 transition-colors min-[1024px]:hidden"
        aria-label="Open watchlist"
      >
        <List className="w-6 h-6 text-white" />
        {/* Count badge */}
        {symbols.length > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[20px] h-5 px-1 bg-argus-loss rounded-full text-white text-xs font-medium flex items-center justify-center">
            {symbols.length}
          </span>
        )}
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
                symbols={sortedSymbols}
                isLoading={isLoading}
                onSymbolClick={(symbol) => {
                  onSymbolClick?.(symbol);
                  setMobileOpen(false); // Close panel after clicking
                }}
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
  onSymbolClick?: (symbol: string) => void;
}

function WatchlistContent({ symbols, isLoading, onSymbolClick }: WatchlistContentProps) {
  const sortMode = useWatchlistUIStore((s) => s.sortMode);
  const setSortMode = useWatchlistUIStore((s) => s.setSortMode);

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
      {/* Header with sort control */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-argus-border">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-argus-accent shrink-0" />
          <span className="text-sm font-medium text-argus-text">Watchlist</span>
          <span className="text-xs text-argus-text-dim">({symbols.length})</span>
        </div>

        {/* Sort dropdown */}
        <SortDropdown value={sortMode} onChange={setSortMode} />
      </div>

      {/* Symbol list */}
      <div className="flex-1 overflow-y-auto">
        {symbols.map((item) => (
          <WatchlistItem key={item.symbol} item={item} onClick={onSymbolClick} />
        ))}
      </div>
    </>
  );
}

interface SortDropdownProps {
  value: WatchlistSortMode;
  onChange: (value: WatchlistSortMode) => void;
}

const sortLabels: Record<WatchlistSortMode, string> = {
  gap: 'Gap %',
  strategy: 'Strategy',
  state: 'State',
};

function SortDropdown({ value, onChange }: SortDropdownProps) {
  return (
    <div className="relative group">
      <button
        className="flex items-center gap-1 px-2 py-1 text-xs text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 rounded transition-colors"
        aria-label="Sort watchlist"
      >
        <span>{sortLabels[value]}</span>
        <ChevronDown className="w-3 h-3" />
      </button>

      {/* Dropdown menu */}
      <div className="absolute right-0 top-full mt-1 bg-argus-surface-2 border border-argus-border rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 min-w-[80px]">
        {(Object.keys(sortLabels) as WatchlistSortMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => onChange(mode)}
            className={`w-full text-left px-3 py-1.5 text-xs hover:bg-argus-surface-3 transition-colors ${
              value === mode ? 'text-argus-accent font-medium' : 'text-argus-text'
            }`}
          >
            {sortLabels[mode]}
          </button>
        ))}
      </div>
    </div>
  );
}

function WatchlistItemSkeleton() {
  return (
    <div className="py-1.5 px-2 border-b border-argus-border/50">
      <div className="flex items-center gap-2 mb-1">
        <Skeleton width={48} height={14} />
        <Skeleton width={50} height={12} />
        <Skeleton width={60} height={16} className="ml-auto" />
        <Skeleton width={36} height={16} />
      </div>
      <div className="flex gap-1">
        <Skeleton width={32} height={14} />
        <Skeleton width={32} height={14} />
      </div>
    </div>
  );
}
