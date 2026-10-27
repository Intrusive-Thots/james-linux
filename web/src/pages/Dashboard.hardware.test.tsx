import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Dashboard } from './Dashboard';

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

vi.mock('../components/ui/RadarScanner', () => ({
  RadarScanner: () => <div data-testid="radar" />,
}));
vi.mock('../components/ui/SignalScope', () => ({
  SignalScope: () => <div data-testid="scope" />,
}));
vi.mock('../components/ui/ProgressBar', () => ({
  ProgressBar: () => null,
}));
vi.mock('../components/ui/ActivityCard', () => ({
  ActivityCard: () => <div data-testid="activity" />,
}));

const baseState = {
  aps: [],
  handshakes: [],
  logs: [],
  adapter: '',
  adapterMode: '',
  scanning: false,
  attack: { stage: 'idle' },
  selectedAP: null,
  currentWorkspace: 'agent',
  currentSubPage: 'dashboard',
};

describe('Dashboard Hardware Status', () => {
  it('distinguishes backend unreachable from missing adapter', () => {
    const { rerender } = render(
      <Dashboard
        state={baseState as any}
        onNavigate={vi.fn()}
        connected={false}
      />
    );
    expect(screen.getByText('UNREACHABLE')).toBeDefined();
    expect(screen.getByText('Backend unreachable')).toBeDefined();
    expect(screen.queryByText('No adapter detected')).toBeNull();

    rerender(
      <Dashboard
        state={baseState as any}
        onNavigate={vi.fn()}
        connected={true}
      />
    );
    expect(screen.getByText('NO ADAPTER')).toBeDefined();
    expect(screen.getByText('No adapter detected')).toBeDefined();
    expect(screen.queryByText('Backend unreachable')).toBeNull();

    rerender(
      <Dashboard
        state={{ ...baseState, adapter: 'wlan0mon', adapterMode: 'monitor' } as any}
        onNavigate={vi.fn()}
        connected={true}
      />
    );
    expect(screen.getByText('ONLINE')).toBeDefined();
    expect(screen.getByText('wlan0mon')).toBeDefined();
  });
});
