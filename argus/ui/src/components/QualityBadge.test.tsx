/**
 * Tests for QualityBadge component.
 *
 * Sprint 24 Session 9.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QualityBadge } from './QualityBadge';

describe('QualityBadge', () => {
  it('renders grade text', () => {
    render(<QualityBadge grade="A+" />);

    expect(screen.getByText('A+')).toBeInTheDocument();
  });

  it('renders green class for A+ grade', () => {
    const { container } = render(<QualityBadge grade="A+" />);
    const badge = container.querySelector('[data-testid="quality-badge"]');

    expect(badge?.className).toContain('text-emerald-400');
    expect(badge?.className).toContain('bg-emerald-400');
  });

  it('renders green class for A grade', () => {
    const { container } = render(<QualityBadge grade="A" />);
    const badge = container.querySelector('[data-testid="quality-badge"]');

    expect(badge?.className).toContain('text-green-400');
  });

  it('renders amber class for B+ grade', () => {
    const { container } = render(<QualityBadge grade="B+" />);
    const badge = container.querySelector('[data-testid="quality-badge"]');

    expect(badge?.className).toContain('text-amber-400');
  });

  it('renders amber class for B grade', () => {
    const { container } = render(<QualityBadge grade="B" />);
    const badge = container.querySelector('[data-testid="quality-badge"]');

    expect(badge?.className).toContain('text-amber-500');
  });

  it('renders red class for C+ grade', () => {
    const { container } = render(<QualityBadge grade="C+" />);
    const badge = container.querySelector('[data-testid="quality-badge"]');

    expect(badge?.className).toContain('text-red-400');
  });

  it('renders gray class for C grade', () => {
    const { container } = render(<QualityBadge grade="C" />);
    const badge = container.querySelector('[data-testid="quality-badge"]');

    expect(badge?.className).toContain('text-gray-400');
  });

  it('shows score and risk tier in tooltip', () => {
    const { container } = render(
      <QualityBadge grade="A+" score={92.3} riskTier="2.5%" />
    );
    const badge = container.querySelector('[data-testid="quality-badge"]');

    expect(badge?.getAttribute('title')).toBe('A+ (92.3) \u2014 2.5% risk');
  });

  it('shows grade-only tooltip when no score', () => {
    const { container } = render(<QualityBadge grade="B" />);
    const badge = container.querySelector('[data-testid="quality-badge"]');

    expect(badge?.getAttribute('title')).toBe('B');
  });

  it('renders empty state for no grade', () => {
    render(<QualityBadge grade="" />);

    const empty = screen.getByTestId('quality-badge-empty');
    expect(empty).toBeInTheDocument();
    expect(empty.textContent).toBe('—');
  });

  it('renders compact by default', () => {
    const { container } = render(<QualityBadge grade="A+" />);

    // Should render a span, not a div with expanded structure
    expect(container.querySelector('[data-testid="quality-badge-expanded"]')).toBeNull();
    expect(container.querySelector('[data-testid="quality-badge"]')).toBeInTheDocument();
  });

  it('renders expanded mode with components', () => {
    const components = { ps: 85, cq: 70, vp: 60, hm: 90, ra: 75 };

    render(
      <QualityBadge
        grade="A"
        score={76.0}
        riskTier="2.0%"
        components={components}
        compact={false}
      />
    );

    expect(screen.getByTestId('quality-badge-expanded')).toBeInTheDocument();
    expect(screen.getByTestId('quality-components')).toBeInTheDocument();
    expect(screen.getByText('Pattern Strength')).toBeInTheDocument();
    expect(screen.getByText('Catalyst Quality')).toBeInTheDocument();
    expect(screen.getByText('Volume Profile')).toBeInTheDocument();
    expect(screen.getByText('Historical Match')).toBeInTheDocument();
    expect(screen.getByText('Regime Alignment')).toBeInTheDocument();
  });

  it('renders expanded mode without components shows no breakdown', () => {
    render(
      <QualityBadge grade="B+" score={65.0} compact={false} />
    );

    expect(screen.getByTestId('quality-badge-expanded')).toBeInTheDocument();
    expect(screen.queryByTestId('quality-components')).toBeNull();
  });

  it('shows score text in expanded mode', () => {
    render(
      <QualityBadge grade="A-" score={78.5} compact={false} />
    );

    expect(screen.getByText('78.5')).toBeInTheDocument();
  });

  it('shows risk tier text in expanded mode', () => {
    render(
      <QualityBadge grade="A" riskTier="1.5%" compact={false} />
    );

    expect(screen.getByText('1.5% risk')).toBeInTheDocument();
  });
});
