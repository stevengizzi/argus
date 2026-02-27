/**
 * Trade search and linking component.
 *
 * Allows searching for trades by symbol and linking them to journal entries.
 * Displays linked trades as removable chips.
 */

import { useState, useEffect, useRef } from 'react';
import { Search, X, TrendingUp, TrendingDown } from 'lucide-react';
import { getTrades } from '../../../api/client';
import { useSymbolDetailUI } from '../../../stores/symbolDetailUI';
import { StrategyBadge } from '../../../components/Badge';
import type { Trade } from '../../../api/types';

interface TradeSearchInputProps {
  linkedTradeIds: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}

/**
 * Format a date string to compact format (e.g., "Feb 27").
 */
function formatCompactDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format P&L with color class.
 */
function formatPnL(pnl: number | null): { text: string; colorClass: string } {
  if (pnl === null) {
    return { text: '—', colorClass: 'text-argus-text-dim' };
  }
  const sign = pnl >= 0 ? '+' : '';
  return {
    text: `${sign}$${pnl.toFixed(2)}`,
    colorClass: pnl >= 0 ? 'text-argus-profit' : 'text-argus-loss',
  };
}

export function TradeSearchInput({
  linkedTradeIds,
  onChange,
  disabled = false,
}: TradeSearchInputProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [linkedTrades, setLinkedTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const openSymbol = useSymbolDetailUI((s) => s.open);

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setTrades([]);
      setIsDropdownOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const response = await getTrades({ symbol: searchQuery.toUpperCase(), limit: 10 });
        setTrades(response.trades);
        setIsDropdownOpen(response.trades.length > 0);
      } catch (error) {
        console.error('Failed to search trades:', error);
        setTrades([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch linked trades data when linkedTradeIds change
  useEffect(() => {
    if (linkedTradeIds.length === 0) {
      setLinkedTrades([]);
      return;
    }

    // Fetch trades to get their details
    // Note: In a real implementation, we'd have a batch fetch endpoint
    // For now, we'll fetch recent trades and filter
    const fetchLinkedTrades = async () => {
      try {
        const response = await getTrades({ limit: 100 });
        const linked = response.trades.filter((t) => linkedTradeIds.includes(t.id));
        setLinkedTrades(linked);
      } catch (error) {
        console.error('Failed to fetch linked trades:', error);
      }
    };

    fetchLinkedTrades();
  }, [linkedTradeIds]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle trade selection
  const handleSelectTrade = (trade: Trade) => {
    if (!linkedTradeIds.includes(trade.id)) {
      onChange([...linkedTradeIds, trade.id]);
    }
    setSearchQuery('');
    setIsDropdownOpen(false);
  };

  // Handle trade removal
  const handleRemoveTrade = (tradeId: string) => {
    onChange(linkedTradeIds.filter((id) => id !== tradeId));
  };

  // Handle chip click (opens symbol detail)
  const handleChipClick = (trade: Trade) => {
    openSymbol(trade.symbol);
  };

  return (
    <div ref={containerRef} className="relative space-y-2">
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-argus-text-dim" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onFocus={() => trades.length > 0 && setIsDropdownOpen(true)}
          placeholder="Search trades by symbol..."
          disabled={disabled}
          className="w-full text-sm bg-argus-surface-2 border border-argus-border rounded-md pl-9 pr-3 py-2 text-argus-text placeholder:text-argus-text-dim focus:outline-none focus:border-argus-accent transition-colors disabled:opacity-50"
        />
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-argus-text-dim border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      {/* Dropdown */}
      {isDropdownOpen && trades.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-argus-surface border border-argus-border rounded-md shadow-lg max-h-60 overflow-y-auto">
          {trades.map((trade) => {
            const pnl = formatPnL(trade.pnl_dollars);
            const isLinked = linkedTradeIds.includes(trade.id);
            const SideIcon = trade.side === 'long' ? TrendingUp : TrendingDown;

            return (
              <button
                key={trade.id}
                type="button"
                onClick={() => handleSelectTrade(trade)}
                disabled={isLinked}
                className={`w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-argus-surface-2 transition-colors ${
                  isLinked ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                {/* Symbol and side */}
                <div className="flex items-center gap-2 min-w-0">
                  <SideIcon className={`w-4 h-4 ${trade.side === 'long' ? 'text-argus-profit' : 'text-argus-loss'}`} />
                  <span className="font-medium text-argus-text">{trade.symbol}</span>
                </div>

                {/* Date */}
                <span className="text-xs text-argus-text-dim">
                  {formatCompactDate(trade.entry_time)}
                </span>

                {/* Strategy badge */}
                <StrategyBadge strategyId={trade.strategy_id} />

                {/* P&L */}
                <span className={`text-sm font-medium ml-auto ${pnl.colorClass}`}>
                  {pnl.text}
                </span>

                {/* Linked indicator */}
                {isLinked && (
                  <span className="text-xs text-argus-accent">Linked</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Linked trades chips */}
      {linkedTrades.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {linkedTrades.map((trade) => (
            <div
              key={trade.id}
              className="group flex items-center gap-1.5 pl-2.5 pr-1 py-1 rounded-full bg-argus-surface-2 border border-argus-border text-xs"
            >
              <button
                type="button"
                onClick={() => handleChipClick(trade)}
                className="flex items-center gap-1.5 hover:text-argus-accent transition-colors"
              >
                <span className="font-medium text-argus-text">{trade.symbol}</span>
                <span className="text-argus-text-dim">{formatCompactDate(trade.entry_time)}</span>
              </button>
              <button
                type="button"
                onClick={() => handleRemoveTrade(trade.id)}
                disabled={disabled}
                className="p-0.5 rounded-full hover:bg-argus-surface hover:text-argus-loss transition-colors disabled:opacity-50"
                aria-label={`Remove ${trade.symbol} trade`}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Show abbreviated IDs for trades we couldn't fetch details for */}
      {linkedTradeIds.length > linkedTrades.length && (
        <div className="flex flex-wrap gap-2">
          {linkedTradeIds
            .filter((id) => !linkedTrades.some((t) => t.id === id))
            .map((tradeId) => (
              <div
                key={tradeId}
                className="flex items-center gap-1.5 pl-2.5 pr-1 py-1 rounded-full bg-argus-surface-2 border border-argus-border text-xs"
              >
                <span className="text-argus-text-dim">{tradeId.slice(0, 8)}...</span>
                <button
                  type="button"
                  onClick={() => handleRemoveTrade(tradeId)}
                  disabled={disabled}
                  className="p-0.5 rounded-full hover:bg-argus-surface hover:text-argus-loss transition-colors disabled:opacity-50"
                  aria-label="Remove trade"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
