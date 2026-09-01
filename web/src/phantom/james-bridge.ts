export type JamesSend = (action: string, params?: Record<string, unknown>, id?: string) => void;

export interface JamesBridge {
  connected: boolean;
  adapter: string | null;
  send: JamesSend;
  onBack: () => void;
}

let bridge: JamesBridge | null = null;

export function bindJames(next: JamesBridge | null) {
  bridge = next;
}

export function jamesOnline(): boolean {
  return Boolean(bridge?.connected);
}

export function jamesAdapter(): string {
  return bridge?.adapter || "wlan0";
}

export function jamesSend(action: string, params: Record<string, unknown> = {}, id?: string) {
  if (!bridge?.connected) return;
  bridge.send(action, params, id);
}

export function jamesBack() {
  bridge?.onBack();
}

export function hasJamesHost(): boolean {
  return Boolean(bridge);
}
