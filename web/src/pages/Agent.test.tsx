import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Agent } from './Agent';

// Mock dependencies
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

vi.mock('lucide-react', () => ({
  Terminal: () => <div>Terminal</div>,
  Bot: () => <div>Bot</div>,
  User: () => <div>User</div>,
  Loader2: () => <div>Loader2</div>,
  Send: () => <div>Send</div>,
  Sparkles: () => <div>Sparkles</div>,
  StopCircle: () => <div>StopCircle</div>,
}));

describe('Agent component', () => {
  const mockState = {
    adapter: 'wlan0',
    attack: { stage: 'idle' },
  };

  it('clears input on Escape key', () => {
    const sendMock = vi.fn();
    const addLogMock = vi.fn();

    render(
      <Agent
        state={mockState as any}
        connected={true}
        send={sendMock}
        addLog={addLogMock}
        lastAgentResponse={null}
      />
    );

    const input = screen.getByPlaceholderText(/Type a command/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'some command' } });
    expect(input.value).toBe('some command');
    input.focus();
    expect(document.activeElement).toBe(input);

    fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });
    expect(input.value).toBe('');
    expect(document.activeElement).not.toBe(input);
  });
});
