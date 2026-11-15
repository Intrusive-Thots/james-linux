/** Use the page's API host in both Vite development and the installed client. */
export function webSocketUrl(pageUrl: string, override?: string): string {
  if (override) return override;
  const url = new URL('/ws', pageUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}
