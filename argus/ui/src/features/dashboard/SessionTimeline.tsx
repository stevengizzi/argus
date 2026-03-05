/**
 * Session Timeline showing the trading day with strategy operating windows.
 *
 * Sprint 21d Code Review Fix #4: New component for 3-card row.
 * - Custom SVG horizontal timeline (9:30 AM → 4:00 PM ET)
 * - Strategy operating windows shown as colored bars:
 *   - ORB: 9:35–11:30 (blue)
 *   - Scalp: 9:45–11:30 (purple)
 *   - VWAP: 10:00–12:00 (cyan/teal)
 *   - Afternoon: 2:00–3:30 (amber)
 * - "Now" marker showing current time position
 * - Strategy letters below bars (O, S, V, A)
 */

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Card } from '../../components/Card';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { getStrategyColor } from '../../utils/strategyConfig';

// Trading day boundaries (minutes from midnight ET)
const MARKET_OPEN = 9 * 60 + 30; // 9:30 AM = 570
const MARKET_CLOSE = 16 * 60; // 4:00 PM = 960
const TOTAL_MINUTES = MARKET_CLOSE - MARKET_OPEN; // 390 minutes

// Strategy operating windows (minutes from midnight ET)
interface StrategyWindow {
  id: string;
  letter: string;
  startMinute: number;
  endMinute: number;
  color: string;
  row: number; // For vertical stacking
}

const STRATEGY_WINDOWS: StrategyWindow[] = [
  {
    id: 'strat_orb_breakout',
    letter: 'O',
    startMinute: 9 * 60 + 35, // 9:35 AM
    endMinute: 11 * 60 + 30, // 11:30 AM
    color: getStrategyColor('strat_orb_breakout'),
    row: 0,
  },
  {
    id: 'strat_orb_scalp',
    letter: 'S',
    startMinute: 9 * 60 + 45, // 9:45 AM
    endMinute: 11 * 60 + 30, // 11:30 AM
    color: getStrategyColor('strat_orb_scalp'),
    row: 1,
  },
  {
    id: 'strat_vwap_reclaim',
    letter: 'V',
    startMinute: 10 * 60, // 10:00 AM
    endMinute: 12 * 60, // 12:00 PM
    color: getStrategyColor('strat_vwap_reclaim'),
    row: 2,
  },
  {
    id: 'strat_afternoon_momentum',
    letter: 'A',
    startMinute: 14 * 60, // 2:00 PM
    endMinute: 15 * 60 + 30, // 3:30 PM
    color: getStrategyColor('strat_afternoon_momentum'),
    row: 0, // Can use row 0 since it doesn't overlap with ORB
  },
];

// Convert minutes from midnight to percentage of trading day
function minuteToPercent(minute: number): number {
  const clamped = Math.max(MARKET_OPEN, Math.min(MARKET_CLOSE, minute));
  return ((clamped - MARKET_OPEN) / TOTAL_MINUTES) * 100;
}

// Get current time in ET as minutes from midnight
function getCurrentMinutesET(): number {
  const now = new Date();
  const etString = now.toLocaleString('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: 'numeric',
    hour12: false,
  });
  const [hours, minutes] = etString.split(':').map(Number);
  return hours * 60 + minutes;
}

// Timeline dimensions
const TIMELINE_HEIGHT = 60;
const BAR_HEIGHT = 10;
const BAR_GAP = 2;
const TIMELINE_Y = 20;
const LABEL_Y = 55;

export function SessionTimeline() {
  const navigate = useNavigate();
  const [currentMinute, setCurrentMinute] = useState(getCurrentMinutesET);
  const [isHovered, setIsHovered] = useState(false);
  const isTablet = useMediaQuery('(max-width: 1023px)');

  // Update current time every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMinute(getCurrentMinutesET());
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  const nowPercent = minuteToPercent(currentMinute);
  const isPreMarket = currentMinute < MARKET_OPEN;
  const isAfterHours = currentMinute >= MARKET_CLOSE;

  // Determine which strategies are currently active
  const activeStrategies = useMemo(() => {
    return STRATEGY_WINDOWS.filter(
      (s) => currentMinute >= s.startMinute && currentMinute <= s.endMinute
    ).map((s) => s.id);
  }, [currentMinute]);

  // Time labels - use shorter labels at tablet width to avoid overlap
  const timeLabels = useMemo(() => [
    { minute: MARKET_OPEN, label: isTablet ? '9:30' : '9:30', anchor: 'start' as const },
    { minute: 12 * 60, label: isTablet ? '12' : '12PM', anchor: 'middle' as const, offset: isTablet ? 8 : 0 },
    { minute: MARKET_CLOSE, label: isTablet ? '4' : '4PM', anchor: 'end' as const },
  ], [isTablet]);

  const handleClick = () => {
    navigate('/orchestrator');
  };

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="h-full"
    >
    <Card
      className="h-full flex flex-col cursor-pointer transition-colors hover:border-argus-border-bright"
      onClick={handleClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium uppercase tracking-wider text-argus-text-dim">
          Session Timeline
        </h3>
        <ArrowRight
          className={`w-3.5 h-3.5 text-argus-text-dim transition-opacity ${
            isHovered ? 'opacity-100' : 'opacity-0'
          }`}
        />
      </div>

      {/* SVG Timeline */}
      <div className="flex-1 min-h-0">
        <svg
          width="100%"
          height={TIMELINE_HEIGHT}
          className="overflow-visible"
          preserveAspectRatio="none"
        >
          {/* Background track */}
          <rect
            x="0%"
            y={TIMELINE_Y}
            width="100%"
            height={BAR_HEIGHT * 3 + BAR_GAP * 2}
            rx={4}
            fill="rgba(255, 255, 255, 0.03)"
          />

          {/* Strategy windows */}
          {STRATEGY_WINDOWS.map((strat) => {
            const startPct = minuteToPercent(strat.startMinute);
            const endPct = minuteToPercent(strat.endMinute);
            const widthPct = endPct - startPct;
            const y = TIMELINE_Y + strat.row * (BAR_HEIGHT + BAR_GAP);
            const isActive = activeStrategies.includes(strat.id);

            return (
              <g key={strat.id}>
                {/* Strategy bar */}
                <rect
                  x={`${startPct}%`}
                  y={y}
                  width={`${widthPct}%`}
                  height={BAR_HEIGHT}
                  rx={2}
                  fill={strat.color}
                  opacity={isActive ? 1 : 0.6}
                />
                {/* Strategy letter - centered in bar */}
                <text
                  x={`${startPct + widthPct / 2}%`}
                  y={y + BAR_HEIGHT / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="fill-white text-[8px] font-semibold pointer-events-none"
                  style={{ textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}
                >
                  {strat.letter}
                </text>
              </g>
            );
          })}

          {/* Now marker */}
          {!isAfterHours && (
            <g>
              <line
                x1={`${nowPercent}%`}
                y1={TIMELINE_Y - 4}
                x2={`${nowPercent}%`}
                y2={TIMELINE_Y + BAR_HEIGHT * 3 + BAR_GAP * 2 + 4}
                stroke="#f97316"
                strokeWidth={2}
                strokeLinecap="round"
              />
              {/* Triangle marker at top */}
              <polygon
                points={`${nowPercent}%,${TIMELINE_Y - 4} ${nowPercent - 0.8}%,${TIMELINE_Y - 10} ${nowPercent + 0.8}%,${TIMELINE_Y - 10}`}
                fill="#f97316"
                transform={`translate(0, 0)`}
              />
            </g>
          )}

          {/* Time labels */}
          {timeLabels.map(({ minute, label, anchor, offset }) => (
            <text
              key={minute}
              x={`${minuteToPercent(minute)}%`}
              y={LABEL_Y}
              dx={offset ?? 0}
              textAnchor={anchor}
              className={`fill-argus-text-dim ${isTablet ? 'text-[9px]' : 'text-[10px]'}`}
            >
              {label}
            </text>
          ))}
        </svg>
      </div>

      {/* Status text */}
      <div className="text-[10px] text-argus-text-dim mt-1">
        {isPreMarket && 'Pre-market — strategies activate at open'}
        {isAfterHours && 'After hours — session complete'}
        {!isPreMarket && !isAfterHours && activeStrategies.length > 0 && (
          <>Active: {activeStrategies.map((id) => {
            const strat = STRATEGY_WINDOWS.find((s) => s.id === id);
            return strat?.letter;
          }).join(', ')}</>
        )}
        {!isPreMarket && !isAfterHours && activeStrategies.length === 0 && 'No strategies active'}
      </div>
    </Card>
    </div>
  );
}
