/**
 * Three-zone layout for the Observatory page.
 *
 * Zones:
 * a. Canvas zone (main area) — renders the active view, takes remaining space
 * b. Tier selector (floating right edge of canvas) — vertical stack of tier pills
 * c. Detail panel (right slide-out, 320px) — slides in when symbol selected, pushes canvas
 *
 * Also includes:
 * - Session vitals bar slot at top (placeholder for S9)
 * - Bottom shortcut reference strip with key hints
 */

import { TierSelector } from './TierSelector';
import { SymbolDetailPanel } from './detail/SymbolDetailPanel';
import type { ObservatoryView } from './hooks/useObservatoryKeyboard';

interface ObservatoryLayoutProps {
  currentView: ObservatoryView;
  selectedTierIndex: number;
  onSelectTier: (index: number) => void;
  selectedSymbol: string | null;
  onDeselectSymbol: () => void;
  children: React.ReactNode;
}

const VIEW_LABELS: Record<ObservatoryView, string> = {
  funnel: 'Funnel',
  matrix: 'Matrix',
  timeline: 'Timeline',
  radar: 'Radar',
};

export function ObservatoryLayout({
  currentView,
  selectedTierIndex,
  onSelectTier,
  selectedSymbol,
  onDeselectSymbol,
  children,
}: ObservatoryLayoutProps) {
  return (
    <div className="flex flex-col h-full" data-testid="observatory-layout">
      {/* Session vitals bar — placeholder for S9 */}
      <div
        className="flex items-center h-10 px-4 border-b border-argus-border bg-argus-surface/50 shrink-0"
        data-testid="session-vitals-placeholder"
      >
        <span className="text-[10px] text-argus-text-dim uppercase tracking-wider">
          Session Vitals — Coming Soon
        </span>
      </div>

      {/* Main content area: canvas + tier selector + detail panel */}
      <div className="flex flex-1 min-h-0">
        {/* Canvas zone + tier selector */}
        <div className="flex-1 relative min-w-0">
          {/* Active view canvas */}
          <div className="absolute inset-0" data-testid="observatory-canvas">
            {children}
          </div>

          {/* Tier selector — floating right edge */}
          <div className="absolute right-2 top-1/2 -translate-y-1/2 z-10">
            <TierSelector
              selectedTierIndex={selectedTierIndex}
              onSelectTier={onSelectTier}
            />
          </div>
        </div>

        {/* Detail panel — slide in from right, pushes canvas */}
        <SymbolDetailPanel
          selectedSymbol={selectedSymbol}
          selectedTierIndex={selectedTierIndex}
          onClose={onDeselectSymbol}
        />
      </div>

      {/* Bottom shortcut reference strip */}
      <div
        className="flex items-center gap-4 h-7 px-4 border-t border-argus-border bg-argus-surface/50 shrink-0"
        data-testid="shortcut-strip"
      >
        <ShortcutHint keys="F M R T" label="views" />
        <ShortcutHint keys="[ ]" label="tiers" />
        <ShortcutHint keys="Tab" label="symbols" />
        <ShortcutHint keys="Enter" label="select" />
        <ShortcutHint keys="Esc" label="close" />
        <ShortcutHint keys="?" label="help" />
      </div>
    </div>
  );
}

function ShortcutHint({ keys, label }: { keys: string; label: string }) {
  return (
    <span className="flex items-center gap-1 text-[10px] text-argus-text-dim">
      <kbd className="px-1 py-0.5 font-mono bg-argus-surface-2 border border-argus-border rounded text-[9px]">
        {keys}
      </kbd>
      <span>{label}</span>
    </span>
  );
}
