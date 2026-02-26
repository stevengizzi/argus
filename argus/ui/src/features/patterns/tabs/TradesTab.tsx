/**
 * Trades tab for Pattern Library detail view.
 *
 * Thin wrapper around the existing TradeTable component with strategy filter locked.
 * Reuses the existing useTrades hook which supports strategy_id filtering.
 */

import { useState } from 'react';
import { TradeTable } from '../../trades/TradeTable';
import { TradeDetailPanel } from '../../trades/TradeDetailPanel';
import { useTrades } from '../../../hooks/useTrades';
import type { Trade } from '../../../api/types';

const ITEMS_PER_PAGE = 20;

interface TradesTabProps {
  strategyId: string;
}

export function TradesTab({ strategyId }: TradesTabProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);

  const { data, isLoading, isFetching } = useTrades({
    strategy_id: strategyId,
    limit: ITEMS_PER_PAGE,
    offset: (currentPage - 1) * ITEMS_PER_PAGE,
  });

  // Show transition state when fetching new page data
  const isTransitioning = isFetching && !isLoading;

  return (
    <div>
      <TradeTable
        trades={data?.trades ?? []}
        totalCount={data?.total_count ?? 0}
        limit={ITEMS_PER_PAGE}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        onTradeClick={setSelectedTrade}
        isLoading={isLoading}
        isTransitioning={isTransitioning}
      />

      <TradeDetailPanel trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
    </div>
  );
}
