/**
 * React wrapper for the Three.js funnel scene with symbol particles.
 *
 * Lazy-loaded via React.lazy() so Three.js stays out of the main bundle.
 * Handles container sizing, ResizeObserver, cleanup on unmount,
 * WS data subscription, mouse events, tooltip overlay, and symbol selection.
 *
 * Sprint 25, Sessions 6a + 6b.
 */

import { useRef, useEffect, useImperativeHandle, forwardRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FunnelScene } from './three/FunnelScene';
import { getObservatoryPipeline, getToken } from '../../../api/client';
import type { SymbolTierData } from './three/FunnelSymbolManager';
import type { CameraMode } from './three/useCameraTransition';

export interface FunnelViewHandle {
  resetCamera: () => void;
  fitView: () => void;
  getScene: () => FunnelScene | null;
}

interface FunnelViewProps {
  mode?: CameraMode;
  selectedTier: number;
  selectedSymbol?: string | null;
  onSelectSymbol?: (symbol: string) => void;
}

interface TooltipState {
  symbol: string;
  tierName: string;
  x: number;
  y: number;
}

export const FunnelView = forwardRef<FunnelViewHandle, FunnelViewProps>(
  function FunnelView({ mode = 'funnel', selectedTier, selectedSymbol, onSelectSymbol }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const sceneRef = useRef<FunnelScene | null>(null);
    const [tooltip, setTooltip] = useState<TooltipState | null>(null);

    // Track latest callback in ref to avoid re-creating scene on prop change
    const onSelectSymbolRef = useRef(onSelectSymbol);
    onSelectSymbolRef.current = onSelectSymbol;

    useImperativeHandle(ref, () => ({
      resetCamera: () => sceneRef.current?.resetCamera(),
      fitView: () => sceneRef.current?.fitView(),
      getScene: () => sceneRef.current,
    }));

    // Fetch initial pipeline data (symbols per tier)
    const { data: pipelineData } = useQuery({
      queryKey: ['observatory', 'pipeline'],
      queryFn: getObservatoryPipeline,
      refetchInterval: 10_000,
    });

    // Initialize Three.js scene
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      const funnelScene = new FunnelScene(container);
      sceneRef.current = funnelScene;

      // Set symbol interaction callbacks
      funnelScene.setSymbolCallbacks({
        onHoverSymbol: (symbol, screenX, screenY) => {
          if (symbol) {
            const tierName = funnelScene.symbolManager.getTierName(symbol) ?? '';
            setTooltip({ symbol, tierName, x: screenX, y: screenY });
          } else {
            setTooltip(null);
          }
        },
        onSelectSymbol: (symbol) => {
          onSelectSymbolRef.current?.(symbol);
        },
      });

      // Mouse move handler — raycast on move only
      const handleMouseMove = (e: MouseEvent) => {
        funnelScene.raycastSymbols(e.clientX, e.clientY);
      };

      // Click handler
      const handleClick = () => {
        funnelScene.handleSymbolClick();
      };

      const canvas = funnelScene.renderer.domElement;
      canvas.addEventListener('mousemove', handleMouseMove);
      canvas.addEventListener('click', handleClick);

      // ResizeObserver for responsive rendering
      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          if (width > 0 && height > 0) {
            funnelScene.resize(width, height);
          }
        }
      });
      resizeObserver.observe(container);

      return () => {
        canvas.removeEventListener('mousemove', handleMouseMove);
        canvas.removeEventListener('click', handleClick);
        resizeObserver.disconnect();
        funnelScene.dispose();
        sceneRef.current = null;
      };
    }, []);

    // Transition camera when mode changes (funnel ↔ radar)
    useEffect(() => {
      const scene = sceneRef.current;
      if (!scene) return;

      if (mode === 'radar' && scene.cameraMode !== 'radar') {
        scene.transitionToRadar();
      } else if (mode === 'funnel' && scene.cameraMode !== 'funnel') {
        scene.transitionToFunnel();
      }
    }, [mode]);

    // Forward pipeline data to symbol manager
    useEffect(() => {
      if (!sceneRef.current || !pipelineData?.tiers) return;

      const tierMap = new Map<string, SymbolTierData>();
      for (const [tierName, tierInfo] of Object.entries(pipelineData.tiers)) {
        for (const symbol of tierInfo.symbols) {
          tierMap.set(symbol, { tier: tierName, conditionsPassed: 0 });
        }
      }
      sceneRef.current.updateSymbolTiers(tierMap);
    }, [pipelineData]);

    // WebSocket subscription for live tier transitions — triggers pipeline refetch
    const queryClient = useQueryClient();

    useEffect(() => {
      const token = getToken();
      if (!token) return;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/v1/observatory`;

      let ws: WebSocket;
      try {
        ws = new WebSocket(wsUrl);
      } catch {
        return;
      }

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'auth', token }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'tier_transition' || msg.type === 'pipeline_update') {
            // Invalidate pipeline query to trigger immediate refetch.
            // The symbol manager handles tier change animation when
            // updateSymbolTiers detects a tier change for a symbol.
            queryClient.invalidateQueries({
              queryKey: ['observatory', 'pipeline'],
            });
          }
        } catch {
          // Ignore malformed messages
        }
      };

      return () => {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close(1000, 'Funnel unmount');
        }
      };
    }, [queryClient]);

    // Update tier highlight when selection changes
    useEffect(() => {
      sceneRef.current?.highlightTier(selectedTier);
    }, [selectedTier]);

    // Update selected symbol highlight
    useEffect(() => {
      sceneRef.current?.symbolManager.setSelectedSymbol(selectedSymbol ?? null);
    }, [selectedSymbol]);

    return (
      <div
        ref={containerRef}
        className="w-full h-full relative"
        data-testid="funnel-view"
      >
        {/* Tooltip overlay */}
        {tooltip && (
          <div
            className="fixed z-50 pointer-events-none px-2 py-1 rounded bg-black/80 border border-argus-border text-xs font-mono text-argus-text shadow-lg"
            style={{
              left: tooltip.x + 12,
              top: tooltip.y - 8,
            }}
            data-testid="funnel-tooltip"
          >
            <span className="font-semibold text-argus-accent">{tooltip.symbol}</span>
            <span className="text-argus-text-dim ml-1.5">{tooltip.tierName}</span>
          </div>
        )}
      </div>
    );
  },
);
