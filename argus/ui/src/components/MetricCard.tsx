import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export function MetricCard({ label, value, subValue, trend, className = '' }: MetricCardProps) {
  const trendIcon = trend === 'up' ? (
    <TrendingUp className="w-3 h-3 text-argus-profit" />
  ) : trend === 'down' ? (
    <TrendingDown className="w-3 h-3 text-argus-loss" />
  ) : trend === 'neutral' ? (
    <Minus className="w-3 h-3 text-argus-text-dim" />
  ) : null;

  return (
    <div className={`text-center ${className}`}>
      <p className="text-xs text-argus-text-dim uppercase tracking-wide mb-1">
        {label}
      </p>
      <div className="flex items-center justify-center gap-1">
        <p className="text-lg font-medium tabular-nums">{value}</p>
        {trendIcon}
      </div>
      {subValue && (
        <p className="text-xs text-argus-text-dim mt-0.5">{subValue}</p>
      )}
    </div>
  );
}
