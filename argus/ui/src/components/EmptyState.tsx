import { isValidElement, type ReactNode, type ReactElement } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  /** Icon component (LucideIcon) or pre-rendered icon element (ReactElement) */
  icon?: LucideIcon | ReactElement;
  message: string;
  action?: ReactNode;
}

export function EmptyState({ icon = Inbox, message, action }: EmptyStateProps) {
  // Handle both component and element forms
  const renderedIcon = isValidElement(icon) ? (
    <div className="mb-4">{icon}</div>
  ) : (
    <IconWrapper Icon={icon as LucideIcon} />
  );

  return (
    <div className="flex flex-col items-center justify-center py-12 text-argus-text-dim">
      {renderedIcon}
      <p className="text-sm mb-4">{message}</p>
      {action && <div>{action}</div>}
    </div>
  );
}

function IconWrapper({ Icon }: { Icon: LucideIcon }) {
  return <Icon className="w-12 h-12 mb-4 opacity-50" />;
}
