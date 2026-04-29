/**
 * Tests for AppShell keyboard shortcuts.
 *
 * Sprint 32.75, Session 12f.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock all heavy dependencies so we can test the keyboard handler in isolation
vi.mock('./Sidebar', () => ({ Sidebar: () => null }));
vi.mock('./MobileNav', () => ({ MobileNav: () => null }));
vi.mock('../stores/live', () => ({
  useLiveStore: (sel: (s: { connect: () => void; disconnect: () => void }) => unknown) =>
    sel({ connect: vi.fn(), disconnect: vi.fn() }),
}));
vi.mock('../stores/copilotUI', () => ({
  useCopilotUIStore: (sel: (s: { toggle: () => void }) => unknown) =>
    sel({ toggle: vi.fn() }),
}));
vi.mock('../features/symbol', () => ({ SymbolDetailPanel: () => null }));
vi.mock('../features/copilot', () => ({
  CopilotPanel: () => null,
  CopilotButton: () => null,
}));
vi.mock('../components/AlertBanner', () => ({ AlertBanner: () => null }));
vi.mock('../components/AlertToast', () => ({ AlertToastStack: () => null }));

// Capture navigate calls
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { AppShell } from './AppShell';

function renderShell() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <AppShell />
    </MemoryRouter>,
  );
}

describe('AppShell keyboard shortcuts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    renderShell();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('key 4 navigates to /arena', () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '4', bubbles: true }));
    expect(mockNavigate).toHaveBeenCalledWith('/arena');
  });

  it('key 0 navigates to /experiments', () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '0', bubbles: true }));
    expect(mockNavigate).toHaveBeenCalledWith('/experiments');
  });
});
