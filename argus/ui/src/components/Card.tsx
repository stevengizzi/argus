interface CardProps {
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
  /** Enable hover lift effect for clickable cards */
  interactive?: boolean;
  /** Click handler for interactive cards */
  onClick?: () => void;
}

export function Card({
  children,
  className = '',
  noPadding = false,
  interactive = false,
  onClick,
}: CardProps) {
  return (
    <div
      className={`bg-argus-surface border border-argus-border rounded-lg ${
        noPadding ? '' : 'p-4'
      } ${interactive ? 'interactive-card' : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      {children}
    </div>
  );
}
