/**
 * Tests for CatalystBadge component.
 *
 * Sprint 23.5 Session 5: Frontend — Dashboard Catalyst Badges + Orchestrator Alert Panel
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CatalystBadge } from './CatalystBadge';
import type { CatalystItem } from '../hooks/useCatalysts';

const createCatalyst = (overrides: Partial<CatalystItem> = {}): CatalystItem => ({
  symbol: 'AAPL',
  catalyst_type: 'earnings',
  quality_score: 85,
  headline: 'AAPL Q4 Earnings Beat Expectations',
  summary: 'Apple beats earnings',
  source: 'SEC',
  source_url: 'https://sec.gov/filing',
  filing_type: '10-K',
  published_at: '2026-03-10T08:00:00Z',
  classified_at: '2026-03-10T08:01:00Z',
  ...overrides,
});

describe('CatalystBadge', () => {
  it('renders nothing when no catalysts', () => {
    const { container } = render(<CatalystBadge catalysts={[]} />);

    expect(container.firstChild).toBeNull();
  });

  it('renders badge with count when catalysts exist', () => {
    const catalysts = [createCatalyst(), createCatalyst({ headline: 'Another' })];

    render(<CatalystBadge catalysts={catalysts} />);

    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders badge with single catalyst count', () => {
    render(<CatalystBadge catalysts={[createCatalyst()]} />);

    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('uses correct color for earnings catalyst type', () => {
    const catalysts = [createCatalyst({ catalyst_type: 'earnings' })];

    const { container } = render(<CatalystBadge catalysts={catalysts} />);
    const badge = container.querySelector('span');

    expect(badge?.className).toContain('text-blue-400');
    expect(badge?.className).toContain('bg-blue-400');
  });

  it('uses correct color for insider_trade catalyst type', () => {
    const catalysts = [createCatalyst({ catalyst_type: 'insider_trade' })];

    const { container } = render(<CatalystBadge catalysts={catalysts} />);
    const badge = container.querySelector('span');

    expect(badge?.className).toContain('text-amber-400');
  });

  it('uses correct color for analyst_action catalyst type', () => {
    const catalysts = [createCatalyst({ catalyst_type: 'analyst_action' })];

    const { container } = render(<CatalystBadge catalysts={catalysts} />);
    const badge = container.querySelector('span');

    expect(badge?.className).toContain('text-purple-400');
  });

  it('uses correct color for regulatory catalyst type', () => {
    const catalysts = [createCatalyst({ catalyst_type: 'regulatory' })];

    const { container } = render(<CatalystBadge catalysts={catalysts} />);
    const badge = container.querySelector('span');

    expect(badge?.className).toContain('text-red-400');
  });

  it('uses highest priority catalyst type color when multiple types', () => {
    // earnings (priority 0) should win over insider_trade (priority 1)
    const catalysts = [
      createCatalyst({ catalyst_type: 'insider_trade' }),
      createCatalyst({ catalyst_type: 'earnings' }),
    ];

    const { container } = render(<CatalystBadge catalysts={catalysts} />);
    const badge = container.querySelector('span');

    // Should use earnings color (blue), not insider_trade (amber)
    expect(badge?.className).toContain('text-blue-400');
  });

  it('shows headline in title attribute for tooltip', () => {
    const headline = 'Test Headline for Tooltip';
    const catalysts = [createCatalyst({ headline })];

    const { container } = render(<CatalystBadge catalysts={catalysts} />);
    const badge = container.querySelector('span');

    expect(badge?.getAttribute('title')).toBe(headline);
  });

  it('falls back to "other" color for unknown catalyst type', () => {
    const catalysts = [createCatalyst({ catalyst_type: 'unknown_type' })];

    const { container } = render(<CatalystBadge catalysts={catalysts} />);
    const badge = container.querySelector('span');

    expect(badge?.className).toContain('text-gray-400');
  });
});
