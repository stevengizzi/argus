interface CardProps {
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
}

export function Card({ children, className = '', noPadding = false }: CardProps) {
  return (
    <div
      className={`bg-argus-surface border border-argus-border rounded-lg ${
        noPadding ? '' : 'p-4'
      } ${className}`}
    >
      {children}
    </div>
  );
}
