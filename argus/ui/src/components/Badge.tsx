interface BadgeProps {
  children: React.ReactNode;
  variant: 'info' | 'success' | 'warning' | 'danger' | 'neutral';
}

const variantClasses: Record<BadgeProps['variant'], string> = {
  info: 'text-argus-accent bg-argus-accent/15',
  success: 'text-argus-profit bg-argus-profit-dim',
  warning: 'text-argus-warning bg-argus-warning-dim',
  danger: 'text-argus-loss bg-argus-loss-dim',
  neutral: 'text-argus-text-dim bg-argus-surface-2',
};

export function Badge({ children, variant }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${variantClasses[variant]}`}
    >
      {children}
    </span>
  );
}
