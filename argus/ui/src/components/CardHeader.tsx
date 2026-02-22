interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export function CardHeader({ title, subtitle, action }: CardHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div>
        <h3 className="text-sm font-medium uppercase tracking-wider text-argus-text-dim">
          {title}
        </h3>
        {subtitle && (
          <p className="text-xs text-argus-text-dim mt-0.5">{subtitle}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
