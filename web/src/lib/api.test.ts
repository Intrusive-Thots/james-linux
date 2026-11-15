import { describe, expect, it } from 'vitest';
import { webSocketUrl } from './api';

describe('API WebSocket URL', () => {
  it('uses the HTTP page host and custom port', () => {
    expect(webSocketUrl('http://127.0.0.1:8877/')).toBe('ws://127.0.0.1:8877/ws');
  });

  it('uses secure WebSockets for a remote HTTPS page', () => {
    expect(webSocketUrl('https://james.example/settings?tab=tools')).toBe('wss://james.example/ws');
  });

  it('uses the Vite host so the configured WebSocket proxy receives development traffic', () => {
    expect(webSocketUrl('http://localhost:5173/')).toBe('ws://localhost:5173/ws');
  });

  it('preserves IPv6 hosts', () => {
    expect(webSocketUrl('http://[::1]:8745/')).toBe('ws://[::1]:8745/ws');
  });

  it('preserves an explicit API WebSocket URL override', () => {
    expect(webSocketUrl('https://james.example/', 'wss://api.example:9000/ws'))
      .toBe('wss://api.example:9000/ws');
  });
});
