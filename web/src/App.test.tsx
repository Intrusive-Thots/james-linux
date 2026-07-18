import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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
  it('changes workspace to settings on Digit7', () => {
    render(<App />);
    // Check initial state is NOT settings (Dashboard is active)
    expect(screen.queryByText('Advanced')).toBeNull();

    // Fire digit 7
    fireEvent.keyDown(window, { code: 'Digit7', altKey: true });

    // Now it should show "Advanced" (which is a Settings subpage)
    expect(screen.getByText('Advanced')).toBeDefined();
  });
});
