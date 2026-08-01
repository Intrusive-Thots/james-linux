import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Handshakes } from './Handshakes';

// Mock dependencies
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

vi.mock('lucide-react', () => ({
  FileKey: () => <div>FileKey</div>,
  Key: () => <div>Key</div>,
  Lock: () => <div>Lock</div>,
  Download: () => <div>Download</div>,
  Trash2: () => <div>Trash2</div>,
  Clock: () => <div>Clock</div>,
  HardDrive: () => <div>HardDrive</div>,
  Search: () => <div>Search</div>,
}));

describe('Handshakes component', () => {
  const mockState = {
    handshakes: [
      { id: '1', essid: 'HomeNet', bssid: '00:11:22', capturedAt: 'now', filePath: '/tmp/1', cracked: false },
      { id: '2', essid: 'Office', bssid: 'AA:BB:CC', capturedAt: 'now', filePath: '/tmp/2', cracked: true },
    ]
  };

  it('filters handshakes and clears filter on Escape key', () => {
    const onRemoveHandshakeMock = vi.fn();

    render(
      <Handshakes
        state={mockState as any}
        onRemoveHandshake={onRemoveHandshakeMock}
      />
    );

    const input = screen.getByPlaceholderText(/Filter by SSID, BSSID.../i) as HTMLInputElement;

    // Initial state: both should be visible
    expect(screen.getByText('HomeNet')).toBeDefined();
    expect(screen.getByText('Office')).toBeDefined();

    // Filter
    fireEvent.change(input, { target: { value: 'Home' } });
    expect(input.value).toBe('Home');

    // Verify filtering
    expect(screen.getByText('HomeNet')).toBeDefined();
    expect(screen.queryByText('Office')).toBeNull();

    // Escape
    input.focus();
    expect(document.activeElement).toBe(input);

    fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });
    expect(input.value).toBe('');
    expect(document.activeElement).not.toBe(input);

    // Verify clear filter shows both again
    expect(screen.getByText('HomeNet')).toBeDefined();
    expect(screen.getByText('Office')).toBeDefined();
  });
});
