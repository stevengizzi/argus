/**
 * Compact regime dimension indicators for the session vitals bar.
 *
 * Displays 6 RegimeVector dimensions + overall confidence in a
 * single horizontal row. Handles null/missing data gracefully.
 *
 * Sprint 27.6, Session 10.
 */

import type { RegimeVectorSummary } from '../../../api/types';

interface RegimeVitalsProps {
  regime: RegimeVectorSummary | null;
}

function trendColor(score: number): string {
  if (score > 0.3) return 'text-emerald-400';
  if (score < -0.3) return 'text-red-400';
  return 'text-argus-text-dim';
}

function trendLabel(score: number): string {
  if (score > 0.3) return 'Bullish';
  if (score < -0.3) return 'Bearish';
  return 'Neutral';
}

function volDirectionArrow(direction: number): string {
  if (direction > 0.2) return '\u2191';
  if (direction < -0.2) return '\u2193';
  return '\u2192';
}

function correlationColor(regime: string | null): string {
  if (regime === 'dispersed') return 'text-emerald-400 bg-emerald-400/10';
  if (regime === 'concentrated') return 'text-red-400 bg-red-400/10';
  return 'text-blue-400 bg-blue-400/10';
}

function sectorPhaseColor(phase: string | null): string {
  if (phase === 'risk_on') return 'text-emerald-400 bg-emerald-400/10';
  if (phase === 'risk_off') return 'text-red-400 bg-red-400/10';
  if (phase === 'transitioning') return 'text-amber-400 bg-amber-400/10';
  return 'text-blue-400 bg-blue-400/10';
}

function sectorPhaseLabel(phase: string | null): string {
  if (phase === 'risk_on') return 'Risk On';
  if (phase === 'risk_off') return 'Risk Off';
  if (phase === 'transitioning') return 'Transition';
  if (phase === 'mixed') return 'Mixed';
  return 'N/A';
}

function intradayColor(character: string | null): string {
  if (character === 'trending') return 'text-emerald-400 bg-emerald-400/10';
  if (character === 'choppy') return 'text-amber-400 bg-amber-400/10';
  if (character === 'reversal') return 'text-purple-400 bg-purple-400/10';
  if (character === 'breakout') return 'text-cyan-400 bg-cyan-400/10';
  return 'text-argus-text-dim bg-argus-surface-2';
}

function intradayLabel(character: string | null): string {
  if (character === null) return 'Pre-market';
  return character.charAt(0).toUpperCase() + character.slice(1);
}

function confidenceBarColor(confidence: number): string {
  if (confidence >= 0.7) return 'bg-emerald-400';
  if (confidence >= 0.4) return 'bg-amber-400';
  return 'bg-red-400';
}

function DimLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[8px] text-argus-text-dim uppercase tracking-wider">
      {children}
    </span>
  );
}

function Divider() {
  return <div className="w-px h-4 bg-argus-border shrink-0" />;
}

export function RegimeVitals({ regime }: RegimeVitalsProps) {
  if (regime === null) {
    return null;
  }

  return (
    <div
      className="flex items-center gap-2 shrink-0"
      data-testid="regime-vitals"
    >
      <Divider />

      {/* Trend */}
      <div className="flex flex-col items-center" data-testid="regime-trend">
        <span className={`text-[10px] font-mono font-semibold ${trendColor(regime.trend_score)}`}>
          {trendLabel(regime.trend_score)}
        </span>
        <DimLabel>Trend</DimLabel>
      </div>

      {/* Volatility */}
      <div className="flex flex-col items-center" data-testid="regime-volatility">
        <span className="text-[10px] font-mono font-semibold text-argus-text tabular-nums">
          {regime.volatility_level.toFixed(1)}
          <span className="ml-0.5">{volDirectionArrow(regime.volatility_direction)}</span>
        </span>
        <DimLabel>Vol</DimLabel>
      </div>

      {/* Breadth */}
      <div className="flex flex-col items-center" data-testid="regime-breadth">
        {regime.universe_breadth_score !== null ? (
          <div className="flex items-center gap-0.5">
            <div className="w-8 h-1.5 bg-argus-surface-2 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  regime.universe_breadth_score >= 0
                    ? 'bg-emerald-400 ml-[50%]'
                    : 'bg-red-400 mr-[50%] float-right'
                }`}
                style={{
                  width: `${Math.abs(regime.universe_breadth_score) * 50}%`,
                }}
              />
            </div>
            {regime.breadth_thrust && (
              <span className="text-[8px] text-amber-400 font-bold" data-testid="breadth-thrust">
                !
              </span>
            )}
          </div>
        ) : (
          <span className="text-[9px] text-argus-text-dim italic" data-testid="breadth-warming">
            Warming up...
          </span>
        )}
        <DimLabel>Breadth</DimLabel>
      </div>

      {/* Correlation */}
      <div className="flex flex-col items-center" data-testid="regime-correlation">
        {regime.correlation_regime !== null ? (
          <span
            className={`text-[9px] font-medium rounded px-1 py-0.5 leading-none ${correlationColor(regime.correlation_regime)}`}
          >
            {regime.correlation_regime}
          </span>
        ) : (
          <span className="text-[9px] text-argus-text-dim">—</span>
        )}
        <DimLabel>Corr</DimLabel>
      </div>

      {/* Sector Rotation */}
      <div className="flex flex-col items-center" data-testid="regime-sector">
        <span
          className={`text-[9px] font-medium rounded px-1 py-0.5 leading-none ${sectorPhaseColor(regime.sector_rotation_phase)}`}
        >
          {sectorPhaseLabel(regime.sector_rotation_phase)}
        </span>
        <DimLabel>Sector</DimLabel>
      </div>

      {/* Intraday Character */}
      <div className="flex flex-col items-center" data-testid="regime-intraday">
        <span
          className={`text-[9px] font-medium rounded px-1 py-0.5 leading-none ${intradayColor(regime.intraday_character)}`}
          data-testid="intraday-badge"
        >
          {intradayLabel(regime.intraday_character)}
        </span>
        <DimLabel>Intraday</DimLabel>
      </div>

      {/* Confidence */}
      <div className="flex flex-col items-center" data-testid="regime-confidence">
        <div className="flex items-center gap-1">
          <div className="w-8 h-1.5 bg-argus-surface-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${confidenceBarColor(regime.regime_confidence)}`}
              style={{ width: `${regime.regime_confidence * 100}%` }}
            />
          </div>
          <span className="text-[9px] font-mono text-argus-text tabular-nums">
            {(regime.regime_confidence * 100).toFixed(0)}%
          </span>
        </div>
        <DimLabel>Conf</DimLabel>
      </div>
    </div>
  );
}
