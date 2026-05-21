"""
JAMES Remote Control Server.

Lightweight HTTP server that exposes JAMES agent commands
via a web API + slick browser-based UI. Access JAMES from
any device on the same network.

Security: A random bearer token is generated on each startup.
The token is displayed in the terminal and embedded in the web UI.
All /api/cmd requests require the token via Authorization header.

Usage:
    server = RemoteServer(agent, port=1337)
    server.start()   # starts in background thread
    server.stop()
"""

import json
import logging
import secrets
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime

from james.utils.net import get_local_ip

logger = logging.getLogger(__name__)


# ── Web UI HTML ────────────────────────────────────────────────
# The {{AUTH_TOKEN}} placeholder is replaced at runtime with the
# session-specific bearer token so the browser UI can authenticate.

WEB_UI_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JAMES — Remote Control</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg-main: #06090f;
  --bg-panel: #0b1120;
  --bg-header: #0d1528;
  --bg-term: #05080f;
  --border: #141e30;
  --cyan: #00f0ff;
  --cyan-dim: #00f0ff40;
  --green: #00ff88;
  --text: #c8d6e5;
  --muted: #5a8aaa;
}
body {
  background: var(--bg-main);
  color: var(--text);
  font-family: 'Inter', sans-serif;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.header {
  background: linear-gradient(90deg, var(--bg-panel) 0%, var(--bg-header) 50%, var(--bg-panel) 100%);
  border-bottom: 2px solid var(--cyan-dim);
  padding: 0 20px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: baseline;
  gap: 15px;
}
.header h1 {
  font-size: 24px;
  font-weight: bold;
  color: var(--cyan);
  letter-spacing: 4px;
}
.header .subtitle {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 1px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}
.badge {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid var(--cyan-dim);
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: bold;
  color: var(--cyan);
}
.status {
  color: var(--green);
  font-size: 11px;
  font-weight: bold;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.main-area {
  display: flex;
  flex: 1;
  overflow: hidden;
  padding: 10px;
  gap: 10px;
}
/* LEFT: Command Palette */
.sidebar {
  width: 250px;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.sidebar-header {
  padding: 10px;
  border-bottom: 1px solid var(--border);
  font-weight: bold;
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}
.palette-group {
  padding: 10px;
}
.palette-title {
  font-size: 10px;
  color: var(--muted);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.palette-btn {
  width: 100%;
  background: transparent;
  color: var(--text);
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 8px;
  text-align: left;
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}
.palette-btn:hover {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--cyan-dim);
  color: var(--cyan);
}
/* CENTER: Chat */
.chat-panel {
  flex: 1;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-width: 400px;
}
.context-ticker {
  background: #0a1520;
  border-bottom: 1px solid var(--cyan-dim);
  padding: 6px 12px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--muted);
  display: flex;
  gap: 15px;
  overflow-x: auto;
}
.context-ticker span b { color: var(--cyan); }
.quick-actions {
  display: flex;
  gap: 6px;
  padding: 10px;
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.qa-btn {
  background: #0d1a2a;
  color: var(--text);
  border: 1px solid var(--cyan-dim);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: bold;
  cursor: pointer;
}
.qa-btn:hover { background: #142540; border-color: var(--cyan); color: var(--cyan); }
.qa-btn.danger { border-color: rgba(255, 71, 87, 0.4); color: #ff4757; }
.qa-btn.danger:hover { border-color: #ff4757; background: rgba(255, 71, 87, 0.1); }
.chat-log {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
  font-family: 'Inter', sans-serif;
}
.msg {
  margin-bottom: 15px;
  display: flex;
  flex-direction: column;
}
.msg.user { align-items: flex-end; }
.msg.agent { align-items: flex-start; }
.bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg.user .bubble {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid var(--cyan-dim);
  border-bottom-right-radius: 2px;
}
.msg.agent .bubble {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.4);
  border-bottom-left-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
}
.chat-input {
  padding: 15px;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 10px;
  background: var(--bg-panel);
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
}
.chat-input input {
  flex: 1;
  background: var(--bg-main);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 15px;
  color: var(--cyan);
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  outline: none;
}
.chat-input input:focus { border-color: var(--cyan); }
.chat-input button {
  background: linear-gradient(135deg, var(--cyan), #0088ff);
  color: #000;
  border: none;
  border-radius: 6px;
  padding: 0 25px;
  font-weight: bold;
  font-size: 14px;
  cursor: pointer;
}
/* RIGHT: Terminal */
.terminal-panel {
  width: 350px;
  background: var(--bg-term);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}
.term-header {
  padding: 8px 12px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
  font-size: 11px;
  color: var(--muted);
  font-family: 'JetBrains Mono', monospace;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
}
.term-output {
  flex: 1;
  padding: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text);
  overflow-y: auto;
  white-space: pre-wrap;
  line-height: 1.4;
}
.term-output .sys { color: var(--muted); }
.term-output .cmd { color: var(--cyan); }
</style>
</head>
<body>
<div class="header">
  <div class="header-left">
    <h1>⚡ JAMES</h1>
    <span class="subtitle">Autonomous Pentesting Agent</span>
  </div>
  <div class="header-right">
    <div class="badge">v0.6.3</div>
    <div class="status">● ONLINE</div>
  </div>
</div>

<div class="main-area">
  <!-- LEFT: Command Palette -->
  <div class="sidebar">
    <div class="sidebar-header">Command Palette</div>
    <div class="palette-group">
      <div class="palette-title">Core Actions</div>
      <button class="palette-btn" onclick="send('status')">⚡ Status</button>
      <button class="palette-btn" onclick="send('list interfaces')">📡 Interfaces</button>
      <button class="palette-btn" onclick="send('show loot')">🔑 View Loot</button>
    </div>
    <div class="palette-group">
      <div class="palette-title">Recon & Web</div>
      <button class="palette-btn" onclick="promptSend('scan')">🎯 Scan Target</button>
      <button class="palette-btn" onclick="promptSend('nikto')">🌐 Nikto Scan</button>
      <button class="palette-btn" onclick="promptSend('gobuster')">📁 Dir Bust</button>
    </div>
    <div class="palette-group">
      <div class="palette-title">Wireless</div>
      <button class="palette-btn" onclick="send('scan aps')">📶 Scan APs</button>
      <button class="palette-btn" onclick="send('wifi blitz')">🔥 Auto Blitz</button>
    </div>
    <div class="palette-group">
      <div class="palette-title">Exploitation</div>
      <button class="palette-btn" onclick="promptSend('brute')">🔓 Brute Force</button>
      <button class="palette-btn" onclick="promptSend('smb enum')">📂 SMB Enum</button>
      <button class="palette-btn" onclick="promptSend('sqlmap')">💉 SQLMap</button>
    </div>
  </div>

  <!-- CENTER: Chat -->
  <div class="chat-panel">
    <div class="context-ticker" id="contextBar">
      <span><b>Target:</b> none</span>
      <span><b>Iface:</b> wlan0</span>
    </div>
    <div class="quick-actions">
      <button class="qa-btn" onclick="send('status')">Status</button>
      <button class="qa-btn" onclick="send('list interfaces')">Interfaces</button>
      <button class="qa-btn" onclick="send('arp scan')">ARP Scan</button>
      <button class="qa-btn" onclick="send('scan aps')">Scan APs</button>
      <button class="qa-btn" onclick="send('show loot')">Loot</button>
      <button class="qa-btn danger" onclick="send('kill james')">🛑 Kill All</button>
    </div>
    <div class="chat-log" id="output">
      <div class="msg agent"><div class="bubble">JAMES Remote Control ready. Type a command or use the palette.</div></div>
    </div>
    <div class="chat-input">
      <input type="text" id="cmdInput" placeholder="> Type command..." autocomplete="off" autofocus>
      <button id="sendBtn" onclick="sendInput()">SEND</button>
    </div>
  </div>

  <!-- RIGHT: Terminal -->
  <div class="terminal-panel">
    <div class="term-header">Terminal / Logs</div>
    <div class="term-output" id="termOutput">
      <span class="sys">JAMES Remote Server initialized.</span><br>
      <span class="sys">Listening on :1337</span><br>
    </div>
  </div>
</div>

<script>
const AUTH_TOKEN = '{{AUTH_TOKEN}}';
const output = document.getElementById('output');
const termOutput = document.getElementById('termOutput');
const cmdInput = document.getElementById('cmdInput');
const sendBtn = document.getElementById('sendBtn');
const contextBar = document.getElementById('contextBar');

cmdInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !sendBtn.disabled) sendInput();
});

function addMsg(role, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  div.appendChild(bubble);
  output.appendChild(div);
  output.scrollTop = output.scrollHeight;
}

function addTerm(text, type='sys') {
  const span = document.createElement('span');
  span.className = type;
  span.textContent = text;
  termOutput.appendChild(span);
  termOutput.appendChild(document.createElement('br'));
  termOutput.scrollTop = termOutput.scrollHeight;
}

function send(cmd) {
  addMsg('user', cmd);
  addTerm('> ' + cmd, 'cmd');
  sendBtn.disabled = true;
  cmdInput.disabled = true;

  fetch('/api/cmd', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + AUTH_TOKEN
    },
    body: JSON.stringify({cmd: cmd})
  })
  .then(r => r.json())
  .then(data => {
    addMsg('agent', data.response || '(no response)');
    addTerm(data.response || 'Done.', 'sys');
    if (data.context) updateContext(data.context);
  })
  .catch(err => {
    addMsg('agent', '[ERROR] ' + err.message);
    addTerm('[ERROR] ' + err.message, 'sys');
  })
  .finally(() => {
    sendBtn.disabled = false;
    cmdInput.disabled = false;
    cmdInput.focus();
  });
}

function sendInput() {
  const cmd = cmdInput.value.trim();
  if (!cmd) return;
  cmdInput.value = '';
  send(cmd);
}

function promptSend(prefix) {
  const target = prompt('Enter target (IP/URL/domain):');
  if (target) send(prefix + ' ' + target);
}

function updateContext(ctx) {
  const parts = [];
  if (ctx.target) parts.push('<span><b>Target:</b> ' + ctx.target + '</span>');
  if (ctx.interface) parts.push('<span><b>Iface:</b> ' + ctx.interface + '</span>');
  if (ctx.domain) parts.push('<span><b>Domain:</b> ' + ctx.domain + '</span>');
  if (ctx.bssid) parts.push('<span><b>BSSID:</b> ' + ctx.bssid + '</span>');
  const svcs = ctx.discovered_services || {};
  for (const [t, info] of Object.entries(svcs).slice(0, 2)) {
    if (info.services && info.services.length > 0) {
      parts.push('<span><b>' + t + ':</b> ' + info.services.join(', ') + '</span>');
    }
  }
  if (parts.length === 0) {
    parts.push('<span><b>Status:</b> Idle</span>');
  }
  contextBar.innerHTML = parts.join('');
}

// Initial context fetch
fetch('/api/status', {
  headers: {'Authorization': 'Bearer ' + AUTH_TOKEN}
})
  .then(r => r.json())
  .then(data => {
    if (data.context) updateContext(data.context);
  })
  .catch(e => console.error(e));
</script>
</body>
</html>"""


class _RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for JAMES remote API."""

    def log_message(self, format, *args):
        logger.debug("Remote: %s", format % args)

    def _check_auth(self) -> bool:
        """Verify the Bearer token. Returns True if valid."""
        expected = getattr(self.server, "auth_token", None)
        if not expected:
            return True  # no token configured

        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if secrets.compare_digest(token, expected):
                return True

        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "unauthorized"}).encode("utf-8"))
        return False

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            # Inject the auth token into the HTML template
            token = getattr(self.server, "auth_token", "")
            html = WEB_UI_TEMPLATE.replace("{{AUTH_TOKEN}}", token)
            self._respond_html(html)
        elif path == "/api/context":
            if not self._check_auth():
                return
            agent = self.server.james_agent
            ctx = {
                k: v
                for k, v in agent.context.items()
                if k
                in (
                    "target",
                    "interface",
                    "domain",
                    "target_url",
                    "discovered_services",
                    "lhost",
                    "lport",
                )
            }
            self._respond_json(ctx)
        elif path == "/api/status":
            if not self._check_auth():
                return
            agent = self.server.james_agent
            ctx = {
                k: v
                for k, v in agent.context.items()
                if k
                in (
                    "target",
                    "interface",
                    "domain",
                    "target_url",
                    "discovered_services",
                    "lhost",
                    "lport",
                )
            }
            self._respond_json(
                {
                    "status": "ok",
                    "time": datetime.now().isoformat(),
                    "context": ctx,
                }
            )
        elif path == "/api/health":
            self._respond_json(
                {"status": "ok", "time": datetime.now().isoformat()}
            )
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/cmd":
            if not self._check_auth():
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                cmd = data.get("cmd", "").strip()
                if not cmd:
                    self._respond_json({"error": "empty command"}, 400)
                    return

                agent = self.server.james_agent
                logger.info("Remote command: %s", cmd)
                response = agent.process(cmd)

                # Return response + updated context
                ctx = {
                    k: v
                    for k, v in agent.context.items()
                    if k
                    in (
                        "target",
                        "interface",
                        "domain",
                        "target_url",
                        "discovered_services",
                    )
                }
                self._respond_json(
                    {
                        "response": response,
                        "intent": agent.last_intent,
                        "context": ctx,
                    }
                )
            except Exception as e:
                logger.error("Remote command error: %s", e)
                self._respond_json({"error": str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()

    def _respond_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _respond_json(self, data: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type, Authorization"
        )
        self.end_headers()


class RemoteServer:
    """
    JAMES Remote Control HTTP Server.

    Runs in a background thread, serves a web UI + API
    that lets you control JAMES from any browser on the network.

    A random bearer token is generated on startup to prevent
    unauthenticated access from other devices on the LAN.
    """

    def __init__(self, agent, port: int = 1337):
        self.agent = agent
        self.port = port
        self.server = None
        self._thread = None
        self.running = False
        self.auth_token = secrets.token_urlsafe(32)

    @property
    def url(self) -> str:
        ip = get_local_ip()
        return f"http://{ip}:{self.port}"

    def start(self):
        """Start the remote server in a background thread."""
        if self.running:
            logger.warning(
                "Remote server already running on port %d", self.port
            )
            return

        self.server = HTTPServer(("0.0.0.0", self.port), _RequestHandler)
        self.server.james_agent = self.agent
        self.server.auth_token = self.auth_token
        self.running = True

        self._thread = threading.Thread(
            target=self.server.serve_forever,
            name="JAMES-Remote",
            daemon=True,
        )
        self._thread.start()

        ip = get_local_ip()
        logger.info("🌐 JAMES Remote Control active at %s", self.url)
        logger.info("   🔑 Auth token: %s", self.auth_token)
        logger.info("   Access from any device on your network!")

    def stop(self):
        """Stop the remote server."""
        if self.server:
            self.server.shutdown()
            self.running = False
            logger.info("Remote server stopped.")

    def is_running(self) -> bool:
        return self.running
