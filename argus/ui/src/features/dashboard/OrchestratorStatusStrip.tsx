/**
 * OrchestratorStatusStrip — Single-line data-dense row at top of Dashboard.
 *
 * Sprint 21d Session 4 (DEC-204):
 * - Shows strategy count, deployed capital, risk consumed, and regime badge
 * - Desktop/tablet: horizontal row with "│" dividers
 * - Mobile: 2×2 grid layout
 * - Entire strip is clickable → navigates to Orchestrator page
 * - Graceful fallback when orchestrator unavailable
 */

import { useNavigate } from 'react-router-dom';
import { RegimeBadge } from '../../components/Badge';
import { useOrchestratorStatus } from '../../hooks';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { formatPercent } from '../../utils/format';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function OrchestratorStatusStrip() {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useOrchestratorStatus();
  const isMobile = useMediaQuery('(max-width: 639px)');

  const handleClick = () => {
    navigate('/orchestrator');
  };

  // Offline fallback state
  if (isError || (!isLoading && !data)) {
    return (
      <button
        type="button"
        onClick={handleClick}
        className="w-full bg-argus-surface-2/50 border border-argus-border rounded-lg px-4 py-2 text-left hover:bg-argus-surface-2 transition-colors cursor-pointer"
        data-testid="orchestrator-status-strip"
      >
        <span className="text-sm text-argus-text-dim">
          Orchestrator offline — click to view
        </span>
      </button>
    );
  }

  // Loading state
  if (isLoading || !data) {
    return (
      <div
        className="w-full bg-argus-surface-2/50 border border-argus-border rounded-lg px-4 py-2 animate-pulse"
        data-testid="orchestrator-status-strip-loading"
      >
        <div className="h-5 w-3/4 bg-argus-surface-2 rounded" />
      </div>
    );
  }

  // Compute derived values
  const activeStrategies = data.allocations.filter((a) => a.is_active).length;
  const totalStrategies = data.allocations.length;
  const deployedCapital = data.total_deployed_capital;
  const deployedPct = data.total_deployed_pct;

  // Calculate daily risk consumed as an approximation
  // We show total deployed % as risk indicator (simplified for strip)
  const riskPct = deployedPct;

  const regime = data.regime || 'unknown';

  // Mobile: 2×2 grid layout
  if (isMobile) {
    return (
      <button
        type="button"
        onClick={handleClick}
        className="w-full bg-argus-surface-2/50 border border-argus-border rounded-lg px-4 py-2 text-left hover:bg-argus-surface-2 transition-colors cursor-pointer"
        data-testid="orchestrator-status-strip"
      >
        <div className="grid grid-cols-2 gap-2 text-sm">
          {/* Top row: strategies + capital */}
          <div className="text-argus-text">
            <span className="font-medium">{activeStrategies}</span>
            <span className="text-argus-text-dim"> strategies</span>
          </div>
          <div className="text-argus-text text-right">
            <span className="font-medium">{formatCurrency(deployedCapital)}</span>
            <span className="text-argus-text-dim"> ({formatPercent(deployedPct)})</span>
          </div>

          {/* Bottom row: risk + regime */}
          <div className="text-argus-text">
            <span className="text-argus-text-dim">Risk: </span>
            <span className="font-medium">{formatPercent(riskPct)}</span>
          </div>
          <div className="flex justify-end">
            <RegimeBadge regime={regime} />
          </div>
        </div>
      </button>
    );
  }

  // Desktop/tablet: horizontal row with dividers
  return (
    <button
      type="button"
      onClick={handleClick}
      className="w-full bg-argus-surface-2/50 border border-argus-border rounded-lg px-4 py-2 text-left hover:bg-argus-surface-2 transition-colors cursor-pointer"
      data-testid="orchestrator-status-strip"
    >
      <div className="flex items-center gap-3 text-sm">
        {/* Strategies */}
        <div className="text-argus-text">
          <span className="font-medium">{activeStrategies}</span>
          <span className="text-argus-text-dim">/{totalStrategies} strategies active</span>
        </div>

        <span className="text-argus-border">│</span>

        {/* Deployed capital */}
        <div className="text-argus-text">
          <span className="font-medium">{formatCurrency(deployedCapital)}</span>
          <span className="text-argus-text-dim"> deployed ({formatPercent(deployedPct)})</span>
        </div>

        <span className="text-argus-border">│</span>

        {/* Risk */}
        <div className="text-argus-text">
          <span className="text-argus-text-dim">Risk: </span>
          <span className="font-medium">{formatPercent(riskPct)}</span>
          <span className="text-argus-text-dim"> of daily</span>
        </div>

        <span className="text-argus-border">│</span>

        {/* Regime badge */}
        <RegimeBadge regime={regime} />
      </div>
    </button>
  );
}
