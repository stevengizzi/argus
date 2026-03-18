/**
 * Vertical tier selector for the Observatory page.
 *
 * Displays 7 pipeline tiers as pills with symbol counts.
 * Floats on the right edge of the canvas zone.
 * Keyboard navigation: [ and ] cycle tiers.
 */

import { useQuery } from '@tanstack/react-query';
import { getObservatoryPipeline } from '../../api/client';
import { PIPELINE_TIERS, type PipelineTier } from './hooks/useObservatoryKeyboard';

function usePipelineTiers() {
  return useQuery({
    queryKey: ['observatory', 'pipeline'],
    queryFn: getObservatoryPipeline,
    refetchInterval: 5_000,
  });
}

interface TierSelectorProps {
  selectedTierIndex: number;
  onSelectTier: (index: number) => void;
}

export function TierSelector({ selectedTierIndex, onSelectTier }: TierSelectorProps) {
  const { data } = usePipelineTiers();

  const getTierCount = (tier: PipelineTier): number => {
    if (!data?.tiers) return 0;
    const key = tier.toLowerCase().replace('-', '_');
    return data.tiers[key]?.count ?? 0;
  };

  return (
    <div
      className="flex flex-col gap-1.5 py-2"
      data-testid="tier-selector"
      role="listbox"
      aria-label="Pipeline tiers"
    >
      {PIPELINE_TIERS.map((tier, index) => {
        const isActive = index === selectedTierIndex;
        const count = getTierCount(tier);

        return (
          <button
            key={tier}
            onClick={() => onSelectTier(index)}
            role="option"
            aria-selected={isActive}
            data-testid={`tier-pill-${tier.toLowerCase().replace('-', '_')}`}
            className={`
              flex items-center justify-between gap-2 px-3 py-1.5 rounded-md
              text-xs font-medium transition-colors whitespace-nowrap
              ${
                isActive
                  ? 'bg-argus-accent/20 text-argus-accent border border-argus-accent/40'
                  : 'text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2/50 border border-transparent'
              }
            `}
          >
            <span>{tier}</span>
            <span
              className={`
                tabular-nums text-[10px] px-1.5 py-0.5 rounded-full min-w-[24px] text-center
                ${isActive ? 'bg-argus-accent/30 text-argus-accent' : 'bg-argus-surface-2 text-argus-text-dim'}
              `}
            >
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
