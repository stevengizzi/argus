/**
 * Intelligence tab for Pattern Library detail view.
 *
 * Placeholder showing upcoming AI-powered features for Sprint 25.
 */

import { Sparkles } from 'lucide-react';
import { EmptyState } from '../../../components/EmptyState';

export function IntelligenceTab() {
  return (
    <div className="py-8">
      <EmptyState icon={Sparkles} message="Intelligence features coming in Sprint 25" />
      <div className="mt-4 text-center text-sm text-argus-text-dim max-w-md mx-auto">
        <p>This tab will show:</p>
        <ul className="mt-2 space-y-1 text-left pl-4">
          <li>• Pattern strength scoring logic</li>
          <li>• Quality grade breakdown for this pattern</li>
          <li>• Historical win rate by quality grade</li>
          <li>• Learning Loop insights and recommendations</li>
        </ul>
      </div>
    </div>
  );
}
