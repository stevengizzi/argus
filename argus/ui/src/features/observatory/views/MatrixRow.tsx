/**
 * Single row in the Matrix heatmap view.
 *
 * Renders a symbol ticker, conditions-passed fraction, and colored
 * condition cells (green=pass, red=fail, gray=inactive).
 *
 * Kept intentionally simple for S5b virtualization layer.
 *
 * Sprint 25, Session 5a.
 */

import { useState } from 'react';
import type { ObservatoryConditionDetail } from '../../../api/types';

interface MatrixRowProps {
  symbol: string;
  conditionsPassed: number;
  conditionsTotal: number;
  conditions: ObservatoryConditionDetail[];
  isSelected: boolean;
  onSelect: (symbol: string) => void;
}

export function MatrixRow({
  symbol,
  conditionsPassed,
  conditionsTotal,
  conditions,
  isSelected,
  onSelect,
}: MatrixRowProps) {
  return (
    <tr
      onClick={() => onSelect(symbol)}
      data-testid={`matrix-row-${symbol}`}
      className={`
        cursor-pointer transition-colors
        ${
          isSelected
            ? 'bg-argus-accent/10 outline outline-1 outline-argus-accent/40'
            : 'hover:bg-argus-surface-2/50'
        }
      `}
    >
      {/* Fixed symbol column */}
      <td className="sticky left-0 z-10 bg-argus-surface px-3 py-1.5 text-xs font-mono font-semibold text-argus-text whitespace-nowrap border-r border-argus-border">
        {symbol}
      </td>

      {/* Conditions passed fraction */}
      <td className="px-3 py-1.5 text-xs tabular-nums text-argus-text-dim text-center whitespace-nowrap border-r border-argus-border">
        {conditionsPassed}/{conditionsTotal}
      </td>

      {/* Condition cells */}
      {conditions.map((condition) => (
        <ConditionCell key={condition.name} condition={condition} />
      ))}
    </tr>
  );
}

function ConditionCell({ condition }: { condition: ObservatoryConditionDetail }) {
  const [showTooltip, setShowTooltip] = useState(false);

  const cellColor = condition.actual_value === null
    ? 'bg-[var(--color-background-secondary,#2a2a2e)]'
    : condition.passed
      ? 'bg-[#1D9E75]'
      : 'bg-[#E24B4A]';

  const cellBorder = condition.actual_value === null
    ? 'border-argus-border'
    : condition.passed
      ? 'border-[#1D9E75]/30'
      : 'border-[#E24B4A]/30';

  return (
    <td className="px-1 py-1.5 text-center relative">
      <div
        className={`
          w-7 h-5 rounded-sm mx-auto ${cellColor} border ${cellBorder}
          transition-opacity hover:opacity-80
        `}
        data-testid={`condition-cell-${condition.name}`}
        data-passed={condition.passed}
        data-inactive={condition.actual_value === null}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      />
      {showTooltip && (
        <div
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1.5 rounded bg-argus-surface-2 border border-argus-border shadow-lg text-[10px] whitespace-nowrap pointer-events-none"
          data-testid={`tooltip-${condition.name}`}
        >
          <div className="font-medium text-argus-text">{condition.name}</div>
          <div className="text-argus-text-dim">
            {condition.actual_value === null ? (
              'Not applicable'
            ) : (
              <>
                <span>Actual: {String(condition.actual_value)}</span>
                <span className="mx-1">|</span>
                <span>Required: {String(condition.required_value)}</span>
              </>
            )}
          </div>
        </div>
      )}
    </td>
  );
}
