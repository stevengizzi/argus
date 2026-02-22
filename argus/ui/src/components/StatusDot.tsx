interface StatusDotProps {
  status: 'healthy' | 'degraded' | 'error' | 'unknown';
  pulse?: boolean;
  size?: 'sm' | 'md';
}

const statusColors: Record<StatusDotProps['status'], string> = {
  healthy: 'bg-argus-profit',
  degraded: 'bg-argus-warning',
  error: 'bg-argus-loss',
  unknown: 'bg-argus-text-dim',
};

const sizeClasses: Record<NonNullable<StatusDotProps['size']>, string> = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
};

export function StatusDot({ status, pulse = false, size = 'md' }: StatusDotProps) {
  return (
    <span
      className={`inline-block rounded-full ${statusColors[status]} ${sizeClasses[size]} ${
        pulse ? 'pulse' : ''
      }`}
    />
  );
}
