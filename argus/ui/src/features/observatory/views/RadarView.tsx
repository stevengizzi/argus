/**
 * Radar view — bottom-up perspective of the Funnel scene.
 *
 * This is NOT a separate Three.js scene. It renders the same FunnelView
 * component with mode='radar', which triggers a camera transition to a
 * bottom-up viewpoint. Concentric tier rings become labeled circles with
 * a center "TRIGGER" indicator.
 *
 * Sprint 25, Session 7.
 */

import { forwardRef } from 'react';
import { FunnelView, type FunnelViewHandle } from './FunnelView';

interface RadarViewProps {
  selectedTier: number;
  selectedSymbol?: string | null;
  onSelectSymbol?: (symbol: string) => void;
}

export const RadarView = forwardRef<FunnelViewHandle, RadarViewProps>(
  function RadarView({ selectedTier, selectedSymbol, onSelectSymbol }, ref) {
    return (
      <FunnelView
        ref={ref}
        mode="radar"
        selectedTier={selectedTier}
        selectedSymbol={selectedSymbol}
        onSelectSymbol={onSelectSymbol}
      />
    );
  },
);
