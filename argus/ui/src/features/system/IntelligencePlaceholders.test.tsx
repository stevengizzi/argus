/**
 * Tests for IntelligencePlaceholders component.
 *
 * Sprint 21d, Session 11.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { IntelligencePlaceholders } from './IntelligencePlaceholders';

describe('IntelligencePlaceholders', () => {
  it('renders all 6 intelligence component items', () => {
    render(<IntelligencePlaceholders />);

    // Check header
    expect(screen.getByText('Intelligence Components')).toBeInTheDocument();

    // Check all 6 items are rendered
    expect(screen.getByText('AI Copilot')).toBeInTheDocument();
    expect(screen.getByText('Pre-Market Engine')).toBeInTheDocument();
    expect(screen.getByText('Catalyst Service')).toBeInTheDocument();
    expect(screen.getByText('Order Flow Analyzer')).toBeInTheDocument();
    expect(screen.getByText('Setup Quality Engine')).toBeInTheDocument();
    expect(screen.getByText('Learning Loop')).toBeInTheDocument();

    // Check sprint badges exist
    expect(screen.getByText('Sprint 22')).toBeInTheDocument();
    expect(screen.getAllByText('Sprint 23')).toHaveLength(2); // Pre-Market and Catalyst
    expect(screen.getByText('Sprint 24')).toBeInTheDocument();
    expect(screen.getByText('Sprint 25')).toBeInTheDocument();
    expect(screen.getByText('Sprint 30')).toBeInTheDocument();
  });
});
