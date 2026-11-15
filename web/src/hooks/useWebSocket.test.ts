import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useWebSocket } from './useWebSocket';

class MockWebSocket {
  static OPEN = 1;
  static instances: MockWebSocket[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  send = vi.fn();
  readonly url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}

describe('useWebSocket lifecycle', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('reconnects after a server disconnect', () => {
    const { result, unmount } = renderHook(() => useWebSocket({
      url: 'ws://localhost:8745/ws', onMessage: vi.fn(), reconnectDelay: 100,
    }));
    const socket = MockWebSocket.instances[0];
    act(() => {
      socket.readyState = MockWebSocket.OPEN;
      socket.onopen?.();
    });
    expect(result.current.connected).toBe(true);
    act(() => socket.close());
    expect(result.current.connected).toBe(false);
    act(() => vi.advanceTimersByTime(100));
    expect(MockWebSocket.instances).toHaveLength(2);
    unmount();
  });

  it('does not reconnect when cleanup closes the socket', () => {
    const { unmount } = renderHook(() => useWebSocket({
      url: 'ws://localhost:8745/ws', onMessage: vi.fn(), reconnectDelay: 100,
    }));
    unmount();
    act(() => vi.advanceTimersByTime(100));
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('ignores delayed events from a socket replaced by a URL change', () => {
    const onMessage = vi.fn();
    const { result, rerender, unmount } = renderHook(({ url }) => useWebSocket({
      url, onMessage, reconnectDelay: 100,
    }), { initialProps: { url: 'ws://localhost:8745/ws' } });
    const oldSocket = MockWebSocket.instances[0];
    act(() => {
      oldSocket.readyState = MockWebSocket.OPEN;
      oldSocket.onopen?.();
    });
    expect(result.current.connected).toBe(true);
    const delayedOpen = oldSocket.onopen;
    const delayedClose = oldSocket.onclose;
    const delayedMessage = oldSocket.onmessage;
    rerender({ url: 'ws://localhost:8746/ws' });
    expect(result.current.connected).toBe(false);
    act(() => delayedOpen?.());
    expect(result.current.connected).toBe(false);
    act(() => {
      delayedClose?.();
      delayedMessage?.({ data: '{"type":"scan_status","scanning":true}' });
      vi.advanceTimersByTime(100);
    });
    expect(result.current.connected).toBe(false);
    expect(onMessage).not.toHaveBeenCalled();
    expect(MockWebSocket.instances.map(socket => socket.url)).toEqual([
      'ws://localhost:8745/ws', 'ws://localhost:8746/ws',
    ]);
    unmount();
  });
});
