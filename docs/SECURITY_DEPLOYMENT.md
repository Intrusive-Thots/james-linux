# JAMES API security and deployment

## Safe default

Both supported Python entry points bind the API to loopback by default:

```bash
python3 main.py --server
# or
python3 -m james.api.server
```

The API is intended to be local-only unless you deliberately configure remote access. The health endpoint is public; when `JAMES_API_TOKEN` is configured, other REST routes require the `X-JAMES-API-Token` header and the WebSocket requires a `token` query parameter.

## Direct remote binding

Do not expose the API over plain HTTP/WebSocket. Direct remote binding is refused unless all of the following are set:

- `JAMES_API_HOST` (for example, `0.0.0.0`)
- `JAMES_API_TOKEN` (use a long random secret)
- `JAMES_API_SSL_CERTFILE`
- `JAMES_API_SSL_KEYFILE`

Example for a controlled test environment:

```bash
export JAMES_API_HOST=0.0.0.0
export JAMES_API_PORT=8745
export JAMES_API_TOKEN="$(openssl rand -hex 32)"
export JAMES_API_SSL_CERTFILE=/path/to/fullchain.pem
export JAMES_API_SSL_KEYFILE=/path/to/private-key.pem
python3 main.py --server
```

Configure the web client with a secure WebSocket URL, such as `VITE_API_WS_URL=wss://your-host.example/ws`. In the web UI, open **Settings → General → Remote API authentication**, enter the same token, and choose **Save & reconnect**. The browser stores the token in session storage, not persistent local storage.

## Reverse-proxy deployment

Prefer terminating TLS at a properly configured reverse proxy and keep the JAMES API bound to `127.0.0.1`. Ensure the proxy forwards WebSocket upgrades, restricts access to trusted users/networks, and does not log the WebSocket token query string. Use a VPN or equivalent access control where possible.

## Autonomous coding agent

The self-improvement loop is opt-in via `JAMES_AUTO_AGENT=1`. It now refuses to edit a dirty working tree or the `main`/`master` branch, does not install requirements automatically, does not run destructive Git reset/clean commands, and does not commit changes automatically. Generated edits are left for human review. Run it only in a disposable worktree or dedicated repair branch.

## Remaining limitations

The shared token is a basic access-control layer, not a substitute for a proper identity provider, per-user authorization, rate limiting, or hardened deployment. Do not expose the API directly to the public internet. Audit the complete application and test the deployment in an isolated environment before using it for real assessments.
