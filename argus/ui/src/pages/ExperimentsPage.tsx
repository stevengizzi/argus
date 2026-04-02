/**
 * Experiments Dashboard — page 9 of the Command Center.
 *
 * Shows variant status table (grouped by pattern), promotion event log,
 * and pattern-level variant comparison. Handles disabled state (503) and
 * empty state (no variants).
 *
 * Read-only — no promote/demote/trigger actions.
 *
 * Sprint 32.5, Session 7 (DEF-131).
 */

import { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, ArrowUp, ArrowDown } from 'lucide-react';
import { useExperimentVariants, usePromotionEvents } from '../hooks/useExperiments';
import { ApiError } from '../api/client';
import type { ExperimentVariant } from '../api/types';

// ─── helpers ────────────────────────────────────────────────────────────────

function abbrev(id: string, len = 8): string {
  return id.length > len ? `${id.slice(0, len)}…` : id;
}

function fmtPct(v: number | null): string {
  if (v === null) return '—';
  return `${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | null, decimals = 2): string {
  if (v === null) return '—';
  return v.toFixed(decimals);
}

function fmtTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

// ─── sub-components ─────────────────────────────────────────────────────────

type SortKey = 'mode' | 'trade_count' | 'shadow_trade_count' | 'win_rate' | 'expectancy' | 'sharpe';
type SortDir = 'asc' | 'desc';

interface SortState {
  key: SortKey;
  dir: SortDir;
}

function ModeBadge({ mode }: { mode: string }) {
  if (mode === 'live') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider bg-argus-profit/20 text-argus-profit">
        LIVE
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider bg-argus-surface-2 text-argus-text-dim">
      SHADOW
    </span>
  );
}

function EventTypeBadge({ eventType }: { eventType: string }) {
  const isPromoted = eventType === 'promote' || eventType === 'promoted';
  if (isPromoted) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-argus-profit/20 text-argus-profit">
        <ArrowUp className="w-3 h-3" /> Promoted
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-argus-loss/20 text-argus-loss">
      <ArrowDown className="w-3 h-3" /> Demoted
    </span>
  );
}

interface SortHeaderProps {
  label: string;
  sortKey: SortKey;
  current: SortState | null;
  onSort: (key: SortKey) => void;
}

function SortHeader({ label, sortKey, current, onSort }: SortHeaderProps) {
  const isActive = current?.key === sortKey;
  return (
    <button
      className="flex items-center gap-1 text-xs font-medium text-argus-text-dim hover:text-argus-text transition-colors"
      onClick={() => onSort(sortKey)}
    >
      {label}
      {isActive && (
        current.dir === 'asc'
          ? <ChevronDown className="w-3 h-3" />
          : <ChevronDown className="w-3 h-3 rotate-180" />
      )}
    </button>
  );
}

interface PatternGroupProps {
  patternName: string;
  variants: ExperimentVariant[];
  sort: SortState | null;
  onSort: (key: SortKey) => void;
  selectedPattern: string | null;
  onSelectPattern: (name: string | null) => void;
}

function PatternGroup({
  patternName,
  variants,
  sort,
  onSort,
  selectedPattern,
  onSelectPattern,
}: PatternGroupProps) {
  const isOpen = selectedPattern !== patternName;

  const sorted = useMemo(() => {
    if (!sort) return variants;
    return [...variants].sort((a, b) => {
      if (sort.key === 'mode') {
        const cmp = a.mode.localeCompare(b.mode);
        return sort.dir === 'asc' ? cmp : -cmp;
      }
      const av = a[sort.key] ?? -Infinity;
      const bv = b[sort.key] ?? -Infinity;
      return sort.dir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
  }, [variants, sort]);

  return (
    <div className="border border-argus-border rounded-lg overflow-hidden">
      {/* Group header */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-argus-surface-2/50 hover:bg-argus-surface-2 transition-colors"
        onClick={() => onSelectPattern(isOpen ? patternName : null)}
      >
        <div className="flex items-center gap-2">
          {isOpen
            ? <ChevronDown className="w-4 h-4 text-argus-text-dim" />
            : <ChevronRight className="w-4 h-4 text-argus-text-dim" />}
          <span className="text-sm font-semibold text-argus-text">{patternName}</span>
          <span className="text-xs text-argus-text-dim">({variants.length} variant{variants.length !== 1 ? 's' : ''})</span>
        </div>
        {!isOpen && (
          <span className="text-xs text-argus-accent">Compare →</span>
        )}
      </button>

      {/* Variant rows */}
      {isOpen && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid={`pattern-table-${patternName}`}>
            <thead>
              <tr className="border-b border-argus-border bg-argus-surface/50">
                <th className="px-4 py-2 text-left text-xs font-medium text-argus-text-dim">Variant ID</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-argus-text-dim">Fingerprint</th>
                <th className="px-4 py-2 text-left">
                  <SortHeader label="Mode" sortKey="mode" current={sort} onSort={onSort} />
                </th>
                <th className="px-4 py-2 text-right">
                  <SortHeader label="Trades" sortKey="trade_count" current={sort} onSort={onSort} />
                </th>
                <th className="px-4 py-2 text-right">
                  <SortHeader label="Shadow Trades" sortKey="shadow_trade_count" current={sort} onSort={onSort} />
                </th>
                <th className="px-4 py-2 text-right">
                  <SortHeader label="Win Rate" sortKey="win_rate" current={sort} onSort={onSort} />
                </th>
                <th className="px-4 py-2 text-right">
                  <SortHeader label="Expectancy" sortKey="expectancy" current={sort} onSort={onSort} />
                </th>
                <th className="px-4 py-2 text-right">
                  <SortHeader label="Sharpe" sortKey="sharpe" current={sort} onSort={onSort} />
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((v) => (
                <tr key={v.variant_id} className="border-b border-argus-border/50 hover:bg-argus-surface-2/30 transition-colors">
                  <td className="px-4 py-2 font-mono text-xs text-argus-text-dim">{abbrev(v.variant_id)}</td>
                  <td className="px-4 py-2 font-mono text-xs text-argus-text-dim">{abbrev(v.config_fingerprint, 10)}</td>
                  <td className="px-4 py-2"><ModeBadge mode={v.mode} /></td>
                  <td className="px-4 py-2 text-right tabular-nums">{v.trade_count}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{v.shadow_trade_count}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{fmtPct(v.win_rate)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{fmtNum(v.expectancy)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{fmtNum(v.sharpe)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Collapsed comparison view */}
      {!isOpen && (
        <div className="px-4 py-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-argus-border">
                <th className="pb-2 text-left text-xs text-argus-text-dim">Variant</th>
                <th className="pb-2 text-center text-xs text-argus-text-dim">Mode</th>
                <th className="pb-2 text-right text-xs text-argus-text-dim">Win Rate</th>
                <th className="pb-2 text-right text-xs text-argus-text-dim">Expectancy</th>
                <th className="pb-2 text-right text-xs text-argus-text-dim">Sharpe</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const bestSharpe = Math.max(...variants.map((x) => x.sharpe ?? -Infinity));
                const bestWr = Math.max(...variants.map((x) => x.win_rate ?? -Infinity));
                return variants.map((v) => {
                  const isBestSharpe = v.sharpe !== null && v.sharpe === bestSharpe && variants.length > 1;
                  const isBestWr = v.win_rate !== null && v.win_rate === bestWr && variants.length > 1;
                  return (
                    <tr key={v.variant_id} className="border-b border-argus-border/30">
                      <td className="py-2 font-mono text-xs text-argus-text-dim">{abbrev(v.variant_id)}</td>
                      <td className="py-2 text-center"><ModeBadge mode={v.mode} /></td>
                      <td className={`py-2 text-right tabular-nums text-sm ${isBestWr ? 'text-argus-profit font-semibold' : ''}`}>
                        {fmtPct(v.win_rate)}
                      </td>
                      <td className="py-2 text-right tabular-nums text-sm">{fmtNum(v.expectancy)}</td>
                      <td className={`py-2 text-right tabular-nums text-sm ${isBestSharpe ? 'text-argus-accent font-semibold' : ''}`}>
                        {fmtNum(v.sharpe)}
                      </td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── main page ───────────────────────────────────────────────────────────────

export function ExperimentsPage() {
  const { data: variantsData, error: variantsError, isLoading: variantsLoading } = useExperimentVariants();
  const { data: promotionsData, isLoading: promotionsLoading } = usePromotionEvents({ limit: 50 });

  const [sort, setSort] = useState<SortState | null>(null);
  const [selectedPattern, setSelectedPattern] = useState<string | null>(null);

  function handleSort(key: SortKey) {
    setSort((prev) => {
      if (prev?.key === key) {
        if (prev.dir === 'asc') return { key, dir: 'desc' };
        return null;
      }
      return { key, dir: 'desc' };
    });
  }

  // Check for disabled state (503)
  const isDisabled =
    variantsError instanceof Error &&
    'status' in variantsError &&
    (variantsError as ApiError).status === 503;

  // Group variants by pattern
  const groupedVariants = useMemo(() => {
    if (!variantsData?.variants) return new Map<string, ExperimentVariant[]>();
    const map = new Map<string, ExperimentVariant[]>();
    for (const v of variantsData.variants) {
      const group = map.get(v.pattern_name) ?? [];
      group.push(v);
      map.set(v.pattern_name, group);
    }
    return map;
  }, [variantsData]);

  // ── disabled state ────────────────────────────────────────────────────────
  if (isDisabled) {
    return (
      <div className="space-y-6" data-testid="experiments-disabled">
        <div>
          <h1 className="text-2xl font-bold text-argus-text">Experiments</h1>
          <p className="text-sm text-argus-text-dim mt-1">Parameter sweep pipeline &amp; variant tracking</p>
        </div>
        <div className="flex flex-col items-center justify-center py-20 text-center border border-argus-border rounded-lg bg-argus-surface">
          <div className="w-12 h-12 rounded-full bg-argus-surface-2 flex items-center justify-center mb-4">
            <span className="text-2xl">⚗️</span>
          </div>
          <p className="text-argus-text font-medium mb-1">Experiment pipeline is not enabled</p>
          <p className="text-sm text-argus-text-dim max-w-sm">
            Enable in <code className="font-mono text-argus-accent">config/experiments.yaml</code> to start running parameter sweeps.
          </p>
        </div>
      </div>
    );
  }

  // ── loading state ─────────────────────────────────────────────────────────
  if (variantsLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-argus-text">Experiments</h1>
          <p className="text-sm text-argus-text-dim mt-1">Parameter sweep pipeline &amp; variant tracking</p>
        </div>
        <div className="flex items-center justify-center py-20">
          <span className="text-sm text-argus-text-dim">Loading experiments…</span>
        </div>
      </div>
    );
  }

  const hasVariants = (variantsData?.variants.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-argus-text">Experiments</h1>
        <p className="text-sm text-argus-text-dim mt-1">Parameter sweep pipeline &amp; variant tracking</p>
      </div>

      {/* Variant Status Table */}
      <section>
        <h2 className="text-base font-semibold text-argus-text mb-3">Variant Status</h2>

        {!hasVariants ? (
          <div
            className="flex flex-col items-center justify-center py-16 text-center border border-argus-border rounded-lg bg-argus-surface"
            data-testid="experiments-empty"
          >
            <p className="text-argus-text font-medium mb-1">No experiments have been run yet</p>
            <p className="text-sm text-argus-text-dim max-w-sm">
              Use{' '}
              <code className="font-mono text-argus-accent">scripts/run_experiment.py</code>{' '}
              to run your first parameter sweep.
            </p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="variant-table">
            {[...groupedVariants.entries()].map(([patternName, variants]) => (
              <PatternGroup
                key={patternName}
                patternName={patternName}
                variants={variants}
                sort={sort}
                onSort={handleSort}
                selectedPattern={selectedPattern}
                onSelectPattern={setSelectedPattern}
              />
            ))}
          </div>
        )}
      </section>

      {/* Promotion Event Log */}
      <section>
        <h2 className="text-base font-semibold text-argus-text mb-3">Promotion Log</h2>

        {promotionsLoading ? (
          <div className="flex items-center justify-center py-8 border border-argus-border rounded-lg">
            <span className="text-sm text-argus-text-dim">Loading…</span>
          </div>
        ) : (promotionsData?.events.length ?? 0) === 0 ? (
          <div
            className="flex items-center justify-center py-12 border border-argus-border rounded-lg bg-argus-surface"
            data-testid="promotions-empty"
          >
            <p className="text-sm text-argus-text-dim">No promotion events recorded yet</p>
          </div>
        ) : (
          <div className="border border-argus-border rounded-lg overflow-hidden" data-testid="promotion-log">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-argus-border bg-argus-surface-2/50">
                    <th className="px-4 py-2 text-left text-xs font-medium text-argus-text-dim">Time</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-argus-text-dim">Pattern</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-argus-text-dim">Variant</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-argus-text-dim">Event</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-argus-text-dim">Transition</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-argus-text-dim">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {promotionsData?.events.map((ev) => (
                    <tr key={ev.event_id} className="border-b border-argus-border/50 hover:bg-argus-surface-2/20 transition-colors">
                      <td className="px-4 py-2 text-xs text-argus-text-dim whitespace-nowrap">
                        {fmtTimestamp(ev.timestamp)}
                      </td>
                      <td className="px-4 py-2 text-xs font-medium">{ev.pattern_name ?? '—'}</td>
                      <td className="px-4 py-2 font-mono text-xs text-argus-text-dim">{abbrev(ev.variant_id)}</td>
                      <td className="px-4 py-2"><EventTypeBadge eventType={ev.event_type} /></td>
                      <td className="px-4 py-2 text-xs text-argus-text-dim">
                        {ev.from_mode} → {ev.to_mode}
                      </td>
                      <td className="px-4 py-2 text-xs text-argus-text-dim max-w-xs truncate" title={ev.trigger_reason}>
                        {ev.trigger_reason}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
