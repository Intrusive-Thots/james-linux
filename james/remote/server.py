"""
JAMES Remote Control Server.

Lightweight HTTP server that exposes JAMES agent commands
via a web API + slick browser-based UI. Access JAMES from
any device on the same network.

Usage:
    server = RemoteServer(agent, port=1337)
    server.start()   # starts in background thread
    server.stop()
"""

import json
import logging
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get the machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ── Web UI HTML ────────────────────────────────────────────────

WEB_UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JAMES — Remote Control</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #06090f;
  --surface: #0b1120;
  --border: #141e30;
  --cyan: #00f0ff;
  --green: #22c55e;
  --orange: #ff6b35;
  --red: #ff4757;
  --purple: #a855f7;
  --text: #c8d6e5;
  --muted: #4a5568;
}
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', sans-serif;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header h1 {
  font-size: 18px;
  font-weight: 700;
  color: var(--cyan);
  letter-spacing: 2px;
}
.header .status {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--muted);
}
.header .status .dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--green);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
  gap: 16px;
}
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.quick-actions button {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 12px;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  transition: all 0.2s;
}
.quick-actions button:hover {
  border-color: var(--cyan);
  color: var(--cyan);
  background: #00f0ff10;
}
.quick-actions button.danger:hover {
  border-color: var(--red);
  color: var(--red);
  background: #ff475710;
}
.quick-actions button.web:hover {
  border-color: var(--purple);
  color: var(--purple);
}
.quick-actions button.hack:hover {
  border-color: var(--orange);
  color: var(--orange);
}
.output-area {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  min-height: 400px;
  max-height: 60vh;
  white-space: pre-wrap;
  word-break: break-word;
}
.output-area .msg {
  margin-bottom: 12px;
  padding: 10px 14px;
  border-radius: 8px;
}
.output-area .msg.user {
  background: #00f0ff08;
  border-left: 3px solid var(--cyan);
}
.output-area .msg.agent {
  background: #22c55e08;
  border-left: 3px solid var(--green);
}
.output-area .msg .label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 4px;
}
.output-area .msg.user .label { color: var(--cyan); }
.output-area .msg.agent .label { color: var(--green); }
.input-area {
  display: flex;
  gap: 8px;
}
.input-area input {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 18px;
  color: var(--text);
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.input-area input:focus {
  border-color: var(--cyan);
}
.input-area input::placeholder {
  color: var(--muted);
}
.input-area button {
  background: linear-gradient(135deg, #00f0ff, #0088ff);
  color: #000;
  border: none;
  border-radius: 10px;
  padding: 14px 28px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: transform 0.1s;
}
.input-area button:hover { transform: scale(1.02); }
.input-area button:active { transform: scale(0.98); }
.input-area button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.context-bar {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: var(--muted);
  padding: 8px 0;
  flex-wrap: wrap;
}
.context-bar span {
  background: var(--surface);
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
}
.context-bar span b { color: var(--cyan); }
@media (max-width: 600px) {
  .main { padding: 12px; }
  .quick-actions button { padding: 6px 10px; font-size: 11px; }
  .input-area input { padding: 12px; font-size: 13px; }
  .input-area button { padding: 12px 20px; }
}
</style>
</head>
<body>
<div class="header">
  <h1>⚡ JAMES REMOTE</h1>
  <div class="status">
    <div class="dot"></div>
    <span id="connStatus">Connected</span>
    <span id="contextTarget"></span>
  </div>
</div>

<div class="main">
  <div class="context-bar" id="contextBar"></div>

  <div class="quick-actions">
    <button onclick="send('status')">⚙️ Status</button>
    <button onclick="send('arp scan')">🔍 ARP Scan</button>
    <button onclick="send('list interfaces')">📡 Interfaces</button>
    <button onclick="send('scan aps')">📶 Scan APs</button>
    <button onclick="send('show loot')">🔑 Loot</button>
    <button onclick="send('list skills')">📋 Skills</button>
    <button onclick="promptSend('scan')">🎯 Scan Target</button>
    <button class="web" onclick="promptSend('nikto')">🌐 Nikto</button>
    <button class="web" onclick="promptSend('gobuster')">📁 Dir Bust</button>
    <button class="web" onclick="promptSend('sqlmap')">💉 SQLMap</button>
    <button class="hack" onclick="promptSend('brute')">🔓 Brute</button>
    <button class="hack" onclick="promptSend('smb enum')">📂 SMB</button>
    <button class="hack" onclick="send('wifi blitz')">🔥 Blitz</button>
    <button class="danger" onclick="send('kill james')">🛑 Kill All</button>
    <button onclick="send('help')">❓ Help</button>
    <button onclick="send('report')">📊 Report</button>
  </div>

  <div class="output-area" id="output">
    <div class="msg agent">
      <div class="label">JAMES</div>
      JAMES Remote Control ready. Type a command or click a button above.
    </div>
  </div>

  <div class="input-area">
    <input type="text" id="cmdInput" placeholder="Type a command... (e.g. scan 192.168.1.1)"
           autocomplete="off" autofocus>
    <button id="sendBtn" onclick="sendInput()">SEND</button>
  </div>
</div>

<script>
const output = document.getElementById('output');
const cmdInput = document.getElementById('cmdInput');
const sendBtn = document.getElementById('sendBtn');
const contextBar = document.getElementById('contextBar');

cmdInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !sendBtn.disabled) sendInput();
});

function addMsg(role, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  const label = document.createElement('div');
  label.className = 'label';
  label.textContent = role === 'user' ? 'YOU' : 'JAMES';
  div.appendChild(label);
  div.appendChild(document.createTextNode(text));
  output.appendChild(div);
  output.scrollTop = output.scrollHeight;
}

function send(cmd) {
  addMsg('user', cmd);
  sendBtn.disabled = true;
  cmdInput.disabled = true;

  fetch('/api/cmd', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({cmd: cmd})
  })
  .then(r => r.json())
  .then(data => {
    addMsg('agent', data.response || '(no response)');
    if (data.context) updateContext(data.context);
  })
  .catch(err => {
    addMsg('agent', '[ERROR] ' + err.message);
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
  const svcs = ctx.discovered_services || {};
  for (const [t, info] of Object.entries(svcs).slice(0, 2)) {
    if (info.services && info.services.length > 0) {
      parts.push('<span><b>' + t + ':</b> ' + info.services.join(', ') + '</span>');
    }
  }
  contextBar.innerHTML = parts.join('');
}

// Initial context fetch
fetch('/api/context').then(r => r.json()).then(updateContext).catch(() => {});
</script>
</body>
</html>"""


class _RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for JAMES remote API."""

    def log_message(self, format, *args):
        logger.debug("Remote: %s", format % args)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._respond_html(WEB_UI)
        elif path == "/api/context":
            agent = self.server.james_agent
            ctx = {k: v for k, v in agent.context.items()
                   if k in ("target", "interface", "domain", "target_url",
                            "discovered_services", "lhost", "lport")}
            self._respond_json(ctx)
        elif path == "/api/health":
            self._respond_json({"status": "ok", "time": datetime.now().isoformat()})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/cmd":
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
                ctx = {k: v for k, v in agent.context.items()
                       if k in ("target", "interface", "domain", "target_url",
                                "discovered_services")}
                self._respond_json({
                    "response": response,
                    "intent": agent.last_intent,
                    "context": ctx,
                })
            except Exception as e:
                logger.error("Remote command error: %s", e)
                self._respond_json({"error": str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()

    def _respond_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _respond_json(self, data: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class RemoteServer:
    """
    JAMES Remote Control HTTP Server.

    Runs in a background thread, serves a web UI + API
    that lets you control JAMES from any browser on the network.
    """

    def __init__(self, agent, port: int = 1337):
        self.agent = agent
        self.port = port
        self.server = None
        self._thread = None
        self.running = False

    @property
    def url(self) -> str:
        ip = get_local_ip()
        return f"http://{ip}:{self.port}"

    def start(self):
        """Start the remote server in a background thread."""
        if self.running:
            logger.warning("Remote server already running on port %d", self.port)
            return

        self.server = HTTPServer(("0.0.0.0", self.port), _RequestHandler)
        self.server.james_agent = self.agent
        self.running = True

        self._thread = threading.Thread(
            target=self.server.serve_forever,
            name="JAMES-Remote",
            daemon=True,
        )
        self._thread.start()

        ip = get_local_ip()
        logger.info("🌐 JAMES Remote Control active at %s", self.url)
        logger.info("   Access from any device on your network!")

    def stop(self):
        """Stop the remote server."""
        if self.server:
            self.server.shutdown()
            self.running = False
            logger.info("Remote server stopped.")

    def is_running(self) -> bool:
        return self.running
