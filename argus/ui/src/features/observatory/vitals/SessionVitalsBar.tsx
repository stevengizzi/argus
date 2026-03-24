/**
 * Horizontal vitals bar at the top of the Observatory page.
 *
 * Three sections:
 * - Left: view selector tabs + debrief toggle
 * - Center: session metrics (symbols, evaluations, signals, trades)
 * - Right: diagnostics (connection dots, closest miss, top blocker, market time)
 *
 * Sprint 25, Session 9.
 */

import type { ObservatoryView } from '../hooks/useObservatoryKeyboard';
import type { UseSessionVitalsResult } from '../hooks/useSessionVitals';
import type { UseDebriefModeResult } from '../hooks/useDebriefMode';
import { DebriefDatePicker } from './DebriefDatePicker';
import { RegimeVitals } from './RegimeVitals';

interface SessionVitalsBarProps {
  currentView: ObservatoryView;
  onChangeView: (view: ObservatoryView) => void;
  vitals: UseSessionVitalsResult;
  debrief: UseDebriefModeResult;
}

const VIEW_TABS: { key: ObservatoryView; label: string; hint: string }[] = [
  { key: 'funnel', label: 'Funnel', hint: 'F' },
  { key: 'matrix', label: 'Matrix', hint: 'M' },
  { key: 'timeline', label: 'Timeline', hint: 'T' },
  { key: 'radar', label: 'Radar', hint: 'R' },
];

function ConnectionDot({ label, connected }: { label: string; connected: boolean }) {
  return (
    <span className="flex items-center gap-1 text-[10px] text-argus-text-dim">
      <span
        className={`inline-block w-1.5 h-1.5 rounded-full ${
          connected ? 'bg-emerald-400' : 'bg-red-400'
        }`}
        data-testid={`connection-dot-${label.toLowerCase()}`}
      />
      <span>{label}</span>
    </span>
  );
}

function MetricCell({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex flex-col items-center px-2" data-testid={`metric-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <span className="text-xs font-mono font-semibold text-argus-text tabular-nums">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </span>
      <span className="text-[9px] text-argus-text-dim uppercase tracking-wider">{label}</span>
    </div>
  );
}

export function SessionVitalsBar({
  currentView,
  onChangeView,
  vitals,
  debrief,
}: SessionVitalsBarProps) {
  const { metrics, connectionStatus, closestMiss, topBlocker, marketTime, isLive } = vitals;

  return (
    <div
      className="flex items-center h-10 px-3 border-b border-argus-border bg-argus-surface/50 shrink-0 gap-3"
      data-testid="session-vitals-bar"
    >
      {/* Left section — View tabs + Debrief toggle */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="flex items-center gap-0.5" data-testid="view-tabs">
          {VIEW_TABS.map((tab) => (
            <button
              key={tab.key}
              className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
                currentView === tab.key
                  ? 'bg-argus-surface-2 text-argus-text font-medium'
                  : 'text-argus-text-dim hover:text-argus-text'
              }`}
              onClick={() => onChangeView(tab.key)}
              data-testid={`view-tab-${tab.key}`}
            >
              {tab.label}
              <kbd className="ml-0.5 text-[8px] text-argus-text-dim/50">{tab.hint}</kbd>
            </button>
          ))}
        </div>

        <div className="w-px h-4 bg-argus-border" />

        <DebriefDatePicker
          isDebrief={debrief.isDebrief}
          selectedDate={debrief.selectedDate}
          availableDates={debrief.availableDates}
          validationError={debrief.validationError}
          onSelectDate={debrief.enterDebrief}
          onExitDebrief={debrief.exitDebrief}
        />

        {debrief.isDebrief && (
          <span className="text-[10px] text-amber-400 font-medium" data-testid="debrief-indicator">
            Reviewing {debrief.selectedDate}
          </span>
        )}
      </div>

      {/* Center section — Session metrics */}
      <div className="flex items-center gap-1 mx-auto" data-testid="session-metrics">
        <MetricCell label="Symbols" value={metrics.symbolsReceiving} />
        <div className="w-px h-4 bg-argus-border" />
        <MetricCell label="Evaluations" value={metrics.totalEvaluations} />
        <div className="w-px h-4 bg-argus-border" />
        <MetricCell label="Signals" value={metrics.totalSignals} />
        <div className="w-px h-4 bg-argus-border" />
        <MetricCell label="Trades" value={metrics.totalTrades} />
      </div>

      {/* Regime dimensions */}
      <RegimeVitals regime={vitals.regimeVector} />

      {/* Right section — Diagnostics */}
      <div className="flex items-center gap-3 shrink-0" data-testid="diagnostics-section">
        {isLive ? (
          <>
            <div className="flex items-center gap-2">
              <ConnectionDot label="Databento" connected={connectionStatus.databento} />
              <ConnectionDot label="IBKR" connected={connectionStatus.ibkr} />
            </div>
            <div className="w-px h-4 bg-argus-border" />
          </>
        ) : null}

        {closestMiss && (
          <span
            className="text-[10px] text-argus-text-dim truncate max-w-[140px]"
            title={`${closestMiss.symbol} ${closestMiss.strategy} ${closestMiss.conditions_passed}/${closestMiss.conditions_total}`}
            data-testid="closest-miss"
          >
            <span className="text-argus-text font-medium">{closestMiss.symbol}</span>
            {' '}
            <span>{closestMiss.strategy}</span>
            {' '}
            <span className="text-amber-400">
              {closestMiss.conditions_passed}/{closestMiss.conditions_total}
            </span>
          </span>
        )}

        {topBlocker && (
          <>
            <div className="w-px h-4 bg-argus-border" />
            <span
              className="text-[10px] text-argus-text-dim truncate max-w-[140px]"
              data-testid="top-blocker"
            >
              <span className="text-red-400">{topBlocker.condition_name}</span>
              {' '}
              <span>({topBlocker.percentage.toFixed(0)}%)</span>
            </span>
          </>
        )}

        <div className="w-px h-4 bg-argus-border" />
        <span className="text-[10px] text-argus-text-dim font-mono whitespace-nowrap" data-testid="market-time">
          {marketTime}
        </span>
      </div>
    </div>
  );
}
