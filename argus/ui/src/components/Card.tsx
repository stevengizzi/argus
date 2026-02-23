interface CardProps {
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
  /** Enable hover lift effect for clickable cards */
  interactive?: boolean;
}

export function Card({ children, className = '', noPadding = false, interactive = false }: CardProps) {
  return (
    <div
      className={`bg-argus-surface border border-argus-border rounded-lg ${
        noPadding ? '' : 'p-4'
      } ${interactive ? 'interactive-card' : ''} ${className}`}
    >
      {children}
    </div>
  );
}
