/**
 * Tests for ConfirmModal component.
 *
 * Sprint 21b review fixes.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmModal } from './ConfirmModal';

describe('ConfirmModal', () => {
  it('renders when isOpen is true', () => {
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();

    render(
      <ConfirmModal
        isOpen={true}
        title="Test Modal"
        message="This is a test message"
        confirmText="Confirm"
        isLoading={false}
        variant="info"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    );

    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('This is a test message')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();

    render(
      <ConfirmModal
        isOpen={false}
        title="Test Modal"
        message="This is a test message"
        confirmText="Confirm"
        isLoading={false}
        variant="info"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    );

    expect(screen.queryByText('Test Modal')).not.toBeInTheDocument();
  });

  it('calls onConfirm when confirm button is clicked', () => {
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();

    render(
      <ConfirmModal
        isOpen={true}
        title="Test Modal"
        message="Test message"
        confirmText="Confirm"
        isLoading={false}
        variant="info"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    );

    fireEvent.click(screen.getByText('Confirm'));
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button is clicked', () => {
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();

    render(
      <ConfirmModal
        isOpen={true}
        title="Test Modal"
        message="Test message"
        confirmText="Confirm"
        isLoading={false}
        variant="info"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    );

    fireEvent.click(screen.getByText('Cancel'));
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });

  it('shows "Processing..." when isLoading is true', () => {
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();

    render(
      <ConfirmModal
        isOpen={true}
        title="Test Modal"
        message="Test message"
        confirmText="Confirm"
        isLoading={true}
        variant="info"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    );

    expect(screen.getByText('Processing...')).toBeInTheDocument();
    expect(screen.queryByText('Confirm')).not.toBeInTheDocument();
  });

  it('renders with warning variant', () => {
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();

    render(
      <ConfirmModal
        isOpen={true}
        title="Warning Modal"
        message="Warning message"
        confirmText="Proceed"
        isLoading={false}
        variant="warning"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    );

    expect(screen.getByText('Warning Modal')).toBeInTheDocument();
  });

  it('renders with danger variant', () => {
    const handleConfirm = vi.fn();
    const handleCancel = vi.fn();

    render(
      <ConfirmModal
        isOpen={true}
        title="Danger Modal"
        message="Danger message"
        confirmText="Delete"
        isLoading={false}
        variant="danger"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    );

    expect(screen.getByText('Danger Modal')).toBeInTheDocument();
  });
});
