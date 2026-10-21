import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ConflictBanner } from '../components/ConflictBanner';

describe('ConflictBanner', () => {
  it('renders conflict message and triggers reload on click', () => {
    const handleReload = vi.fn();
    render(
      <ConflictBanner
        message="This work item has changed since you opened it. Please refresh and try again."
        onReload={handleReload}
      />
    );

    expect(screen.getByText('Concurrent Modification Conflict')).toBeInTheDocument();
    expect(
      screen.getByText(/This work item has changed since you opened it/i)
    ).toBeInTheDocument();

    const reloadButton = screen.getByRole('button', { name: /Reload Latest Version/i });
    expect(reloadButton).toBeInTheDocument();

    fireEvent.click(reloadButton);
    expect(handleReload).toHaveBeenCalledTimes(1);
  });

  it('disables button when reload is in progress', () => {
    render(
      <ConflictBanner
        message="Stale version detected"
        onReload={() => {}}
        isLoading={true}
      />
    );

    const reloadButton = screen.getByRole('button', { name: /Reload Latest Version/i });
    expect(reloadButton).toBeDisabled();
  });
});
