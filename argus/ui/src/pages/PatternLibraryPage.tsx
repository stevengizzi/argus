/**
 * Pattern Library page - strategy documentation and analysis hub.
 *
 * Displays all trading strategies with their specs, backtest results,
 * and live performance metrics. Sessions 3-8 will add the full content.
 */

import { BookOpen } from 'lucide-react';
import { AnimatedPage } from '../components/AnimatedPage';

export function PatternLibraryPage() {
  return (
    <AnimatedPage>
      <div className="flex items-center gap-3 mb-6">
        <BookOpen className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Pattern Library</h1>
      </div>
      <div className="text-argus-text-dim">
        Pattern Library content coming in Sessions 3-8.
      </div>
    </AnimatedPage>
  );
}
