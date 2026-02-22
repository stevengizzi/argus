import type { LucideIcon } from 'lucide-react';
import { Inbox } from 'lucide-react';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: LucideIcon;
  message: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon = Inbox, message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-argus-text-dim">
      <Icon className="w-12 h-12 mb-4 opacity-50" />
      <p className="text-sm mb-4">{message}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
