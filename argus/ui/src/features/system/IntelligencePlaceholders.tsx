/**
 * Placeholder cards for future intelligence components.
 *
 * Displays a grid of AI/ML components that will be built in upcoming sprints.
 * Muted styling to indicate these are planned, not active.
 */

import { Brain, Sunrise, Newspaper, BarChart3, Star, RefreshCw, type LucideIcon } from 'lucide-react';
import { Card } from '../../components/Card';
import { CardHeader } from '../../components/CardHeader';

interface IntelligenceItem {
  icon: LucideIcon;
  name: string;
  sprint: number;
  description: string;
}

const INTELLIGENCE_ITEMS: IntelligenceItem[] = [
  {
    icon: Brain,
    name: 'AI Copilot',
    sprint: 22,
    description: 'Contextual Claude chat from every page',
  },
  {
    icon: Sunrise,
    name: 'Pre-Market Engine',
    sprint: 23,
    description: 'Automated 4:00 AM scanning + watchlist',
  },
  {
    icon: Newspaper,
    name: 'Catalyst Service',
    sprint: 23,
    description: 'News/filing classification and scoring',
  },
  {
    icon: BarChart3,
    name: 'Order Flow Analyzer',
    sprint: 24,
    description: 'L2/L3 depth analysis and flow signals',
  },
  {
    icon: Star,
    name: 'Setup Quality Engine',
    sprint: 25,
    description: 'Composite 0–100 trade scoring',
  },
  {
    icon: RefreshCw,
    name: 'Learning Loop',
    sprint: 30,
    description: 'Score calibration and improvement',
  },
];

function SprintBadge({ sprint }: { sprint: number }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-argus-surface-2 text-argus-text-dim">
      Sprint {sprint}
    </span>
  );
}

interface IntelligenceItemCardProps {
  item: IntelligenceItem;
}

function IntelligenceItemCard({ item }: IntelligenceItemCardProps) {
  const Icon = item.icon;
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-argus-surface-2/50 border border-argus-border/50">
      <div className="flex-shrink-0 p-2 rounded-md bg-argus-surface">
        <Icon className="w-4 h-4 text-argus-text-dim" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-argus-text">{item.name}</span>
          <SprintBadge sprint={item.sprint} />
        </div>
        <p className="text-xs text-argus-text-dim">{item.description}</p>
      </div>
    </div>
  );
}

export function IntelligencePlaceholders() {
  return (
    <Card>
      <CardHeader
        title="Intelligence Components"
        subtitle="Upcoming AI capabilities"
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {INTELLIGENCE_ITEMS.map((item) => (
          <IntelligenceItemCard key={item.name} item={item} />
        ))}
      </div>
    </Card>
  );
}
