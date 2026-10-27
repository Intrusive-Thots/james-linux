import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Recon } from './Recon';

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

vi.mock('../components/ui/AirspaceHeatmap', () => ({
  AirspaceHeatmap: () => <div data-testid="heatmap" />,
}));
vi.mock('../components/ui/SignalBars', () => ({
  SignalBars: () => null,
}));
vi.mock('../hooks/useShortcutFocus', () => ({
  useShortcutFocus: () => ({ current: null }),
}));

const emptyState = {
  aps: [],
  handshakes: [],
  logs: [],
  adapter: '',
  adapterMode: '',
  scanning: false,
  attack: { stage: 'idle' },
  selectedAP: null,
};

const withAps = {
  ...emptyState,
  aps: [
    { essid: 'Home', bssid: 'AA', channel: 6, privacy: 'WPA2', power: -40, clients: 2, vendor: 'x' },
    { essid: 'Cafe', bssid: 'BB', channel: 1, privacy: 'OPN', power: -60, clients: 0, vendor: 'y' },
  ],
};

describe('Recon metric cards', () => {
  it('shows zero-state summary when no APs, MiniStats when data exists', () => {
    const { rerender } = render(
      <Recon
        state={emptyState as any}
        onSelectAP={vi.fn()}
        onStartScan={vi.fn()}
        onStopScan={vi.fn()}
        onNavigate={vi.fn()}
      />
    );
    expect(screen.getByText(/No networks discovered yet/i)).toBeDefined();
    expect(screen.queryByText('Total APs')).toBeNull();

    rerender(
      <Recon
        state={withAps as any}
        onSelectAP={vi.fn()}
        onStartScan={vi.fn()}
        onStopScan={vi.fn()}
        onNavigate={vi.fn()}
      />
    );
    expect(screen.getByText('Total APs')).toBeDefined();
    expect(screen.getByText('Encrypted')).toBeDefined();
    expect(screen.queryByText(/No networks discovered yet/i)).toBeNull();
  });
});
