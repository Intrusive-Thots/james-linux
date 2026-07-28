import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentConsole } from './AgentConsole';

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
}));

describe('AgentConsole component', () => {
  const mockState = {
    adapter: 'wlan0',
    attack: { stage: 'idle' },
  };

  it('clears input on Escape key', () => {
    const sendMock = vi.fn();
    const addLogMock = vi.fn();

    render(
      <AgentConsole
        state={mockState as any}
        connected={true}
        send={sendMock}
        addLog={addLogMock}
        lastAgentResponse={null}
      />
    );

    const input = screen.getAllByPlaceholderText(/Type a command/i)[0] as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'some command' } });
    expect(input.value).toBe('some command');

    fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });
    expect(input.value).toBe('');
  });

  it('navigates history with ArrowUp and ArrowDown', () => {
    const sendMock = vi.fn();
    const addLogMock = vi.fn();

    const { rerender } = render(
      <AgentConsole
        state={mockState as any}
        connected={true}
        send={sendMock}
        addLog={addLogMock}
        lastAgentResponse={null}
      />
    );

    const input = screen.getAllByPlaceholderText(/Type a command/i)[0] as HTMLInputElement;

    // Send first command
    fireEvent.change(input, { target: { value: 'cmd1' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    // Simulate agent response to clear processing state
    rerender(<AgentConsole state={mockState as any} connected={true} send={sendMock} addLog={addLogMock} lastAgentResponse={{response: 'ok', ts: 1}} />);

    // Send second command
    fireEvent.change(input, { target: { value: 'cmd2' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    rerender(<AgentConsole state={mockState as any} connected={true} send={sendMock} addLog={addLogMock} lastAgentResponse={{response: 'ok2', ts: 2}} />);

    // Force clear input (react state update sometimes not reflected immediately in input.value in test)
    fireEvent.change(input, { target: { value: '' } });

    expect(input.value).toBe('');

    // Press ArrowUp (should show cmd2)
    fireEvent.keyDown(input, { key: 'ArrowUp', code: 'ArrowUp' });
    expect(input.value).toBe('cmd2');

    // Press ArrowUp again (should show cmd1)
    fireEvent.keyDown(input, { key: 'ArrowUp', code: 'ArrowUp' });
    expect(input.value).toBe('cmd1');

    // Press ArrowDown (should show cmd2)
    fireEvent.keyDown(input, { key: 'ArrowDown', code: 'ArrowDown' });
    expect(input.value).toBe('cmd2');

    // Press ArrowDown again (should clear input)
    fireEvent.keyDown(input, { key: 'ArrowDown', code: 'ArrowDown' });
    expect(input.value).toBe('');
  });
});
