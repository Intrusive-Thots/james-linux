import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // Deprecated
    removeListener: vi.fn(), // Deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock ResizeObserver
window.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;

describe('App shortcuts', () => {
  it('changes workspace to settings on Digit7', async () => {
    render(<App />);
    expect(screen.queryByText('Advanced')).toBeNull();
    fireEvent.keyDown(window, { code: 'Digit7', altKey: true });
    await waitFor(() => expect(screen.getByText('Advanced')).toBeDefined());
  });

  it('changes workspace to auto on Digit8', async () => {
    const { unmount } = render(<App />);
    expect(screen.queryByText('Agent Console')).toBeNull();
    fireEvent.keyDown(window, { code: 'Digit8', altKey: true });
    await waitFor(() => expect(screen.queryAllByText('Agent Console').length).toBeGreaterThan(0));
    unmount();
  });

  it('changes page to autopilot on Digit9', async () => {
    const { unmount } = render(<App />);
    fireEvent.keyDown(window, { code: 'Digit9', altKey: true });
    await waitFor(() => expect(screen.queryAllByText('Auto-Pilot').length).toBeGreaterThan(0));
    unmount();
  });

  it('changes page to console on Digit0', async () => {
    const { unmount } = render(<App />);
    fireEvent.keyDown(window, { code: 'Digit0', altKey: true });
    await waitFor(() => expect(screen.queryAllByText('Agent Console').length).toBeGreaterThan(0));
    unmount();
  });
});
