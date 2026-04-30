/* ── JAMES Remote Dashboard — Client Logic ───────────────── */

const API_BASE = window.location.origin;
const WS_BASE = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host;

let token = localStorage.getItem('james_token') || '';
let ws = null;
let reconnectTimer = null;
const cmdHistory = [];
let historyIdx = -1;

/* ── Auth ──────────────────────────────────────────────────── */

async function doLogin() {
    const key = document.getElementById('api-key-input').value;
    const errEl = document.getElementById('login-error');
    errEl.textContent = '';

    try {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key }),
        });

        if (!res.ok) {
            const data = await res.json();
            errEl.textContent = data.detail || 'Login failed';
            return;
        }

        const data = await res.json();
        token = data.token;
        localStorage.setItem('james_token', token);
        showApp();
    } catch (e) {
        errEl.textContent = 'Connection failed: ' + e.message;
    }
}

function showApp() {
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('app-screen').classList.remove('hidden');
    connectWS();
    addAgentMessage("Hey, I'm JAMES — your autonomous pentesting agent.\n\nConnected remotely. Type 'help' for commands.");
    startClock();
}

/* ── WebSocket ─────────────────────────────────────────────── */

function connectWS() {
    if (ws && ws.readyState <= 1) return;

    const url = `${WS_BASE}/ws?token=${encodeURIComponent(token)}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
        setWsStatus(true);
        clearTimeout(reconnectTimer);
    };

    ws.onclose = () => {
        setWsStatus(false);
        reconnectTimer = setTimeout(connectWS, 3000);
    };

    ws.onerror = () => setWsStatus(false);

    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        handleWSMessage(data);
    };
}

function handleWSMessage(data) {
    switch (data.type) {
        case 'chat_response':
            removeThinking();
            addAgentMessage(data.message);
            break;
        case 'thinking':
            addThinking();
            break;
        case 'shell_response':
            removeThinking();
            addAgentMessage(`$ stdout:\n${data.stdout}\n${data.stderr}`);
            break;
        case 'task_update':
            // auto-refresh log if on that tab
            if (document.getElementById('panel-log').classList.contains('active')) {
                refreshLog();
            }
            break;
        case 'pong':
            break;
    }
}

function setWsStatus(connected) {
    const dot = document.getElementById('ws-status');
    dot.className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
}

function wsSend(data) {
    if (ws && ws.readyState === 1) {
        ws.send(JSON.stringify(data));
    }
}

/* ── Chat ──────────────────────────────────────────────────── */

function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    cmdHistory.push(msg);
    historyIdx = -1;
    addUserMessage(msg);

    // prefer WebSocket for real-time
    if (ws && ws.readyState === 1) {
        wsSend({ type: 'chat', message: msg });
    } else {
        // fallback to REST
        chatREST(msg);
    }
}

async function chatREST(msg) {
    addThinking();
    try {
        const res = await apiFetch('/api/agent/chat', 'POST', { message: msg });
        removeThinking();
        addAgentMessage(res.response);
    } catch (e) {
        removeThinking();
        addAgentMessage('[ERROR] ' + e.message);
    }
}

function addUserMessage(text) {
    const el = document.createElement('div');
    el.className = 'msg user';
    el.innerHTML = `<span class="msg-label">YOU ❯</span>${escapeHtml(text)}`;
    document.getElementById('chat-messages').appendChild(el);
    scrollChat();
}

function addAgentMessage(text) {
    const el = document.createElement('div');
    el.className = 'msg agent';
    el.innerHTML = `<span class="msg-label">JAMES ⚡</span>${escapeHtml(text)}`;
    document.getElementById('chat-messages').appendChild(el);
    scrollChat();
}

function addThinking() {
    const el = document.createElement('div');
    el.className = 'msg thinking';
    el.id = 'thinking-msg';
    el.textContent = '⏳ JAMES is working…';
    document.getElementById('chat-messages').appendChild(el);
    scrollChat();
}

function removeThinking() {
    const el = document.getElementById('thinking-msg');
    if (el) el.remove();
}

function scrollChat() {
    const c = document.getElementById('chat-messages');
    c.scrollTop = c.scrollHeight;
}

/* ── Recon ─────────────────────────────────────────────────── */

async function doQuickScan() {
    const target = document.getElementById('recon-target').value.trim();
    if (!target) return;
    showReconLoading();
    try {
        const data = await apiFetch('/api/recon/quick', 'POST', { target });
        renderRecon(data);
    } catch (e) {
        document.getElementById('recon-results').innerHTML = `<p class="placeholder-text">${e.message}</p>`;
    }
}

async function doFullScan() {
    const target = document.getElementById('recon-target').value.trim();
    if (!target) return;
    showReconLoading();
    try {
        const data = await apiFetch('/api/recon/full', 'POST', { target });
        renderRecon(data);
    } catch (e) {
        document.getElementById('recon-results').innerHTML = `<p class="placeholder-text">${e.message}</p>`;
    }
}

function showReconLoading() {
    document.getElementById('recon-results').innerHTML = '<p class="placeholder-text">Scanning…</p>';
}

function renderRecon(data) {
    const el = document.getElementById('recon-results');
    if (data.error) {
        el.innerHTML = `<p class="placeholder-text">${escapeHtml(data.error)}</p>`;
        return;
    }
    const hosts = data.hosts || [];
    if (!hosts.length) {
        el.innerHTML = '<p class="placeholder-text">No hosts found.</p>';
        return;
    }
    let html = '<table class="results-table"><thead><tr><th>Host</th><th>Port</th><th>State</th><th>Service</th><th>Version</th></tr></thead><tbody>';
    for (const host of hosts) {
        for (const port of (host.ports || [])) {
            html += `<tr><td>${esc(host.address)}</td><td>${port.port}</td><td>${esc(port.state)}</td><td>${esc(port.service)}</td><td>${esc(port.version)}</td></tr>`;
        }
    }
    html += '</tbody></table>';
    el.innerHTML = html;
}

/* ── Wi-Fi ─────────────────────────────────────────────────── */

async function refreshInterfaces() {
    try {
        const data = await apiFetch('/api/wifi/interfaces', 'GET');
        const sel = document.getElementById('wifi-iface');
        sel.innerHTML = '';
        for (const iface of data) {
            const opt = document.createElement('option');
            opt.value = iface.interface;
            opt.textContent = `${iface.interface} (${iface.mode})`;
            sel.appendChild(opt);
        }
        wifiLog('Interfaces refreshed.');
    } catch (e) {
        wifiLog('Error: ' + e.message);
    }
}

async function toggleMonitor() {
    const iface = document.getElementById('wifi-iface').value;
    if (!iface) return;
    const sel = document.getElementById('wifi-iface');
    const opt = sel.options[sel.selectedIndex];
    const action = opt.textContent.includes('Monitor') ? 'disable' : 'enable';
    try {
        await apiFetch('/api/wifi/monitor', 'POST', { interface: iface, action });
        wifiLog(`Monitor mode ${action}d on ${iface}`);
        refreshInterfaces();
    } catch (e) {
        wifiLog('Error: ' + e.message);
    }
}

async function doDeauth() {
    const iface = document.getElementById('wifi-iface').value;
    const bssid = document.getElementById('deauth-bssid').value.trim();
    const count = parseInt(document.getElementById('deauth-count').value) || 10;
    if (!iface || !bssid) return;
    try {
        await apiFetch('/api/wifi/deauth', 'POST', { interface: iface, bssid, count });
        wifiLog(`Sent ${count} deauth frames → ${bssid}`);
    } catch (e) {
        wifiLog('Error: ' + e.message);
    }
}

function wifiLog(text) {
    const el = document.getElementById('wifi-output');
    el.innerHTML += escapeHtml(text) + '\n';
    el.scrollTop = el.scrollHeight;
}

async function doAutoPwn() {
    const iface = document.getElementById('wifi-iface').value;
    const wl = document.getElementById('autopwn-wl').value.trim();
    if (!iface) { wifiLog('Select an interface first.'); return; }
    if (!wl) { wifiLog('Enter a wordlist path.'); return; }

    const btn = document.getElementById('autopwn-btn');
    const status = document.getElementById('autopwn-status');
    btn.disabled = true;
    status.textContent = 'AutoPwn running… Check the Log tab for live progress.';
    wifiLog('[AUTOPWN] Launching autonomous Wi-Fi audit…');

    try {
        const data = await apiFetch('/api/wifi/autopwn', 'POST', { interface: iface, wordlist: wl });
        wifiLog('[AUTOPWN] ' + (data.message || 'Started'));
        // Start polling the log
        const pollId = setInterval(async () => {
            try {
                const log = await apiFetch('/api/log', 'GET');
                const last = log[log.length - 1];
                if (last) {
                    status.textContent = `[${last.status}] ${last.action} (${last.tool})`;
                }
            } catch (_) {}
        }, 3000);
        // Stop polling after 3 minutes max
        setTimeout(() => { clearInterval(pollId); btn.disabled = false; status.textContent += ' (monitoring stopped)'; }, 180000);
    } catch (e) {
        wifiLog('[ERROR] ' + e.message);
        btn.disabled = false;
        status.textContent = 'Failed: ' + e.message;
    }
}

/* ── Cracking ──────────────────────────────────────────────── */

async function doCrackWpa() {
    const cap = document.getElementById('crack-cap').value.trim();
    const wl = document.getElementById('crack-wl').value.trim();
    if (!cap || !wl) return;
    crackLog('Cracking WPA handshake…');
    try {
        const data = await apiFetch('/api/crack/wpa', 'POST', { capture_file: cap, wordlist: wl });
        if (data.found) {
            crackLog(`🔑 KEY FOUND: ${data.key}`);
        } else {
            crackLog('🔒 No key found.');
        }
    } catch (e) {
        crackLog('Error: ' + e.message);
    }
}

async function doCrackHash() {
    const hf = document.getElementById('hash-file').value.trim();
    const wl = document.getElementById('crack-wl').value.trim();
    const mode = parseInt(document.getElementById('hash-mode').value);
    if (!hf || !wl) return;
    crackLog('Cracking hash…');
    try {
        const data = await apiFetch('/api/crack/hash', 'POST', { hash_file: hf, wordlist: wl, hash_mode: mode });
        crackLog(data.output || JSON.stringify(data));
    } catch (e) {
        crackLog('Error: ' + e.message);
    }
}

function crackLog(text) {
    const el = document.getElementById('crack-output');
    el.innerHTML += escapeHtml(text) + '\n';
    el.scrollTop = el.scrollHeight;
}

/* ── Log ───────────────────────────────────────────────────── */

async function refreshLog() {
    try {
        const data = await apiFetch('/api/log', 'GET');
        const el = document.getElementById('log-entries');
        if (!data.length) {
            el.innerHTML = '<p class="placeholder-text">No tasks logged yet.</p>';
            return;
        }
        let html = '';
        for (const e of data) {
            const statusClass = e.status === 'done' ? 'log-status-done' : 'log-status-error';
            html += `<div class="log-entry">
                <span class="log-time">${esc(e.timestamp.substring(0,19))}</span>
                <span class="log-action">${esc(e.action)}</span>
                <span class="log-tool">${esc(e.tool)}</span>
                <span class="${statusClass}">${esc(e.status)}</span>
            </div>`;
        }
        el.innerHTML = html;
    } catch (e) {
        document.getElementById('log-entries').innerHTML = `<p class="placeholder-text">${e.message}</p>`;
    }
}

function exportLog() {
    apiFetch('/api/log', 'GET').then(data => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'james_log.json';
        a.click();
    });
}

/* ── Tab Switching ─────────────────────────────────────────── */

function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => { p.classList.add('hidden'); p.classList.remove('active'); });
    document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');
    const panel = document.getElementById(`panel-${tabId}`);
    panel.classList.remove('hidden');
    panel.classList.add('active');
}

/* ── API Helper ────────────────────────────────────────────── */

async function apiFetch(path, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (token) opts.headers['Authorization'] = `Bearer ${token}`;
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${path}`, opts);
    if (res.status === 401) {
        localStorage.removeItem('james_token');
        location.reload();
        throw new Error('Session expired');
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

/* ── Utilities ─────────────────────────────────────────────── */

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
const esc = escapeHtml;

function startClock() {
    const el = document.getElementById('clock');
    setInterval(() => {
        el.textContent = new Date().toLocaleTimeString();
    }, 1000);
}

/* ── Keyboard ──────────────────────────────────────────────── */

document.addEventListener('keydown', (e) => {
    const input = document.getElementById('chat-input');
    if (document.activeElement === input) {
        if (e.key === 'Enter') sendChat();
        if (e.key === 'ArrowUp' && cmdHistory.length) {
            e.preventDefault();
            if (historyIdx === -1) historyIdx = cmdHistory.length - 1;
            else if (historyIdx > 0) historyIdx--;
            input.value = cmdHistory[historyIdx];
        }
        if (e.key === 'ArrowDown' && cmdHistory.length) {
            e.preventDefault();
            if (historyIdx < cmdHistory.length - 1) { historyIdx++; input.value = cmdHistory[historyIdx]; }
            else { historyIdx = -1; input.value = ''; }
        }
    }

    // handle Enter on login input
    if (document.activeElement === document.getElementById('api-key-input') && e.key === 'Enter') {
        doLogin();
    }
});

/* ── Auto-login if token exists ────────────────────────────── */

if (token) {
    apiFetch('/api/system/status').then(() => showApp()).catch(() => {
        localStorage.removeItem('james_token');
        token = '';
    });
}
