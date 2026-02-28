/**
 * System feature components.
 *
 * Health monitoring, intelligence placeholders, and event logging.
 * Strategy cards and emergency controls moved to Orchestrator (Sprint 21d, DEC-210).
 */

export { SystemOverview } from './SystemOverview';
export { ComponentStatusList } from './ComponentStatus';
export { EventsLog } from './EventsLog';
export { IntelligencePlaceholders } from './IntelligencePlaceholders';

// Legacy exports — kept for Orchestrator page imports
export { StrategyCards } from './StrategyCards';
export { EmergencyControls } from './EmergencyControls';

// Skeleton exports
export {
  SystemSkeleton,
  SystemOverviewSkeleton,
  ComponentStatusListSkeleton,
  StrategyCardsSkeleton,
  EventsLogSkeleton,
} from './SystemSkeleton';
