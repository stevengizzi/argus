/**
 * Per-strategy condition check grid for the Observatory detail panel.
 *
 * Displays pass/fail status for each entry condition with actual vs. required values.
 * Groups conditions by strategy. Within each strategy section, passed conditions
 * sort first, then failed, then inactive.
 *
 * Data source: /api/v1/observatory/symbol/{symbol}/journey — extracts latest
 * ENTRY_EVALUATION events and parses condition details from metadata.
 */

import type { ObservatoryJourneyEvent } from '../../../api/client';

interface ConditionResult {
  name: string;
  passed: boolean | null;
  actualValue: string | null;
  requiredValue: string | null;
}

interface StrategyConditions {
  strategy: string;
  conditions: ConditionResult[];
}

interface SymbolConditionGridProps {
  events: ObservatoryJourneyEvent[];
}

function extractConditions(events: ObservatoryJourneyEvent[]): StrategyConditions[] {
  const entryEvals = events.filter(
    (e) => e.event_type === 'ENTRY_EVALUATION' || e.event_type === 'CONDITION_CHECK'
  );

  const latestByStrategy = new Map<string, ObservatoryJourneyEvent>();
  for (const event of entryEvals) {
    const existing = latestByStrategy.get(event.strategy);
    if (!existing || event.timestamp > existing.timestamp) {
      latestByStrategy.set(event.strategy, event);
    }
  }

  return Array.from(latestByStrategy.entries()).map(([strategy, event]) => {
    const conditions: ConditionResult[] = [];
    const details = event.metadata?.conditions_detail;

    if (Array.isArray(details)) {
      for (const detail of details) {
        const d = detail as Record<string, unknown>;
        conditions.push({
          name: String(d.name ?? 'Unknown'),
          passed: typeof d.passed === 'boolean' ? d.passed : null,
          actualValue: d.actual_value != null ? String(d.actual_value) : null,
          requiredValue: d.required_value != null ? String(d.required_value) : null,
        });
      }
    }

    const sortOrder = (c: ConditionResult): number => {
      if (c.passed === true) return 0;
      if (c.passed === false) return 1;
      return 2;
    };
    conditions.sort((a, b) => sortOrder(a) - sortOrder(b));

    return { strategy, conditions };
  });
}

function ConditionBadge({ passed }: { passed: boolean | null }) {
  if (passed === true) {
    return (
      <span
        className="inline-block px-1.5 py-0.5 text-[9px] font-semibold rounded bg-emerald-500/20 text-emerald-400"
        data-testid="condition-pass"
      >
        PASS
      </span>
    );
  }
  if (passed === false) {
    return (
      <span
        className="inline-block px-1.5 py-0.5 text-[9px] font-semibold rounded bg-red-500/20 text-red-400"
        data-testid="condition-fail"
      >
        FAIL
      </span>
    );
  }
  return (
    <span
      className="inline-block px-1.5 py-0.5 text-[9px] font-semibold rounded bg-argus-surface-2 text-argus-text-dim"
      data-testid="condition-inactive"
    >
      &ndash;
    </span>
  );
}

export function SymbolConditionGrid({ events }: SymbolConditionGridProps) {
  const strategyGroups = extractConditions(events);

  if (strategyGroups.length === 0) {
    return (
      <div className="text-xs text-argus-text-dim" data-testid="condition-grid-empty">
        No evaluation data available
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="condition-grid">
      {strategyGroups.map((group) => (
        <div key={group.strategy}>
          <h4 className="text-[10px] font-semibold text-argus-text-dim uppercase tracking-wider mb-1.5">
            {group.strategy}
          </h4>
          <div className="space-y-1">
            {group.conditions.map((condition, idx) => (
              <div
                key={`${condition.name}-${idx}`}
                className={`flex items-center justify-between px-2 py-1 rounded text-[11px] ${
                  condition.passed === true
                    ? 'bg-emerald-500/5'
                    : condition.passed === false
                      ? 'bg-red-500/5'
                      : 'bg-argus-surface-2/30'
                }`}
                data-testid="condition-row"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <ConditionBadge passed={condition.passed} />
                  <span className="text-argus-text truncate">{condition.name}</span>
                </div>
                <div className="flex items-center gap-1 shrink-0 ml-2 text-[10px]">
                  {condition.actualValue !== null && (
                    <span className="text-argus-text font-mono">{condition.actualValue}</span>
                  )}
                  {condition.requiredValue !== null && (
                    <>
                      <span className="text-argus-text-dim">/</span>
                      <span className="text-argus-text-dim font-mono">{condition.requiredValue}</span>
                    </>
                  )}
                </div>
              </div>
            ))}
            {group.conditions.length === 0 && (
              <div className="text-[10px] text-argus-text-dim px-2 py-1">
                No conditions recorded
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
