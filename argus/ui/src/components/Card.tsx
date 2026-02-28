interface CardProps {
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
  /** Enable hover lift effect for clickable cards */
  interactive?: boolean;
  /** Click handler for interactive cards */
  onClick?: () => void;
  /** Make card fill available height (for matching heights in grid rows) */
  fullHeight?: boolean;
}

export function Card({
  children,
  className = '',
  noPadding = false,
  interactive = false,
  onClick,
  fullHeight = false,
}: CardProps) {
  return (
    <div
      className={`bg-argus-surface border border-argus-border rounded-lg ${
        noPadding ? '' : 'p-4'
      } ${interactive ? 'interactive-card' : ''} ${fullHeight ? 'h-full flex flex-col' : ''} ${className}`}
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
