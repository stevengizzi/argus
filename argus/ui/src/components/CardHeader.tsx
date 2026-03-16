interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
}

export function CardHeader({ title, subtitle, action, icon, badge }: CardHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-3 min-h-10">
      <div className="flex items-center gap-2">
        {icon && <span>{icon}</span>}
        <div>
          <h3 className="text-sm font-medium uppercase tracking-wider text-argus-text-dim">
            {title}
          </h3>
          {subtitle && (
            <p className="text-xs text-argus-text-dim mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {badge}
        {action && <div>{action}</div>}
      </div>
    </div>
  );
}
