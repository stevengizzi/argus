/**
 * Placeholder content for the AI Copilot panel.
 *
 * Displays coming-soon messaging until Sprint 22 activates the Claude integration.
 * Extracted as separate component for clean replacement when live.
 */

import { Bot, Check } from 'lucide-react';

const COPILOT_FEATURES = [
  'Answer questions about any system data',
  'Generate reports saved to The Debrief',
  'Propose parameter and allocation changes',
  'Annotate trades with insights',
  'Explain Orchestrator decisions',
];

export function CopilotPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-8">
      <div className="max-w-sm mx-auto bg-argus-surface-2/50 border border-argus-border rounded-xl p-6 text-center">
        {/* Icon */}
        <div className="flex items-center justify-center mb-4">
          <div className="p-4 rounded-full bg-argus-accent/10">
            <Bot className="w-10 h-10 text-argus-accent" />
          </div>
        </div>

        {/* Heading */}
        <h2 className="text-lg font-semibold text-argus-text mb-2">AI Copilot</h2>

        {/* Description */}
        <p className="text-sm text-argus-text-dim mb-6">
          Contextual AI assistant activating Sprint 22. Soon you'll chat with Claude
          here — page-aware, with full system knowledge.
        </p>

        {/* Feature list */}
        <div className="text-left space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-argus-text-dim mb-2">
            Features coming
          </p>
          {COPILOT_FEATURES.map((feature) => (
            <div key={feature} className="flex items-center gap-2">
              <Check className="w-3.5 h-3.5 text-argus-accent flex-shrink-0" />
              <span className="text-xs text-argus-text">{feature}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
