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
    startClock();
    initBackground();
    showToast('Connected to JAMES agent', 'success');
    // Periodically update system stats
    updateSystemStats();
    setInterval(updateSystemStats, 15000);
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
    const label = document.getElementById('connection-label');
    if (label) label.textContent = connected ? 'live' : 'offline';
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

    // Remove welcome screen on first message
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

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
    const bssid = document.getElementById('crack-bssid').value.trim();
    if (!cap || !wl) return;
    crackLog('⚡ Cracking WPA handshake (aircrack-ng)…');
    try {
        const data = await apiFetch('/api/crack/wpa', 'POST', {
            capture_file: cap, wordlist: wl, bssid: bssid || undefined
        });
        if (data.found) {
            crackLog(`🔑 KEY FOUND: ${data.key}`);
        } else {
            crackLog('🔒 No key found with straight wordlist. Try Smart Crack →');
        }
    } catch (e) {
        crackLog('Error: ' + e.message);
    }
}

async function doSmartCrackWpa() {
    const cap = document.getElementById('crack-cap').value.trim();
    const wl = document.getElementById('crack-wl').value.trim();
    const bssid = document.getElementById('crack-bssid').value.trim();
    if (!cap || !wl) { crackLog('Enter a capture file and wordlist.'); return; }

    showCrackProgress('Smart WPA Crack', ['aircrack-ng', 'hashcat+rules', 'john']);
    crackLog('🧠 Starting Smart WPA Crack (aircrack → hashcat+rules → john)…');
    try {
        const data = await apiFetch('/api/crack/smart', 'POST', {
            capture_file: cap, wordlist: wl, bssid: bssid || undefined
        });
        crackLog(`[STARTED] ${data.message}`);
        startCrackPolling();
    } catch (e) {
        crackLog('Error: ' + e.message);
        hideCrackProgress();
    }
}

async function doCrackHash() {
    const hf = document.getElementById('hash-file').value.trim();
    const wl = document.getElementById('hash-wl').value.trim();
    const mode = parseInt(document.getElementById('hash-mode').value);
    if (!hf || !wl) return;
    crackLog('⚡ Cracking hash (hashcat + auto-rules)…');
    try {
        const data = await apiFetch('/api/crack/hash', 'POST', {
            hash_file: hf, wordlist: wl, hash_mode: mode
        });
        if (data.found && data.cracked_keys) {
            crackLog('🔑 CRACKED:');
            for (const k of data.cracked_keys) {
                crackLog(`  ${k.hash} → ${k.plain}`);
            }
        } else {
            crackLog('🔒 No key found. Try Smart Crack for deeper search →');
        }
        if (data.rules_used && data.rules_used !== 'none') {
            crackLog(`  (rules used: ${data.rules_used})`);
        }
    } catch (e) {
        crackLog('Error: ' + e.message);
    }
}

async function doSmartCrackHash() {
    const hf = document.getElementById('hash-file').value.trim();
    const wl = document.getElementById('hash-wl').value.trim();
    const mode = parseInt(document.getElementById('hash-mode').value);
    if (!hf || !wl) { crackLog('Enter a hash file and wordlist.'); return; }

    showCrackProgress('Smart Hash Crack', ['hashcat', 'hashcat+best64', 'hashcat+rockyou30k', 'john']);
    crackLog('🧠 Starting Smart Hash Crack (cascading strategies)…');
    try {
        const data = await apiFetch('/api/crack/smart', 'POST', {
            hash_file: hf, wordlist: wl, hash_mode: mode
        });
        crackLog(`[STARTED] ${data.message}`);
        startCrackPolling();
    } catch (e) {
        crackLog('Error: ' + e.message);
        hideCrackProgress();
    }
}

function crackLog(text) {
    const el = document.getElementById('crack-output');
    el.innerHTML += escapeHtml(text) + '\n';
    el.scrollTop = el.scrollHeight;
}

// ── Crack Progress UI ──────────────────────────────────

let crackPollId = null;

function showCrackProgress(title, stages) {
    const el = document.getElementById('crack-progress');
    el.style.display = 'block';
    document.getElementById('crack-progress-title').textContent = title;
    const status = document.getElementById('crack-progress-status');
    status.textContent = 'running';
    status.className = 'progress-status running';
    document.getElementById('crack-progress-bar').style.width = '10%';

    const stagesEl = document.getElementById('crack-stages');
    stagesEl.innerHTML = stages.map((s, i) =>
        `<span class="stage-chip ${i === 0 ? 'active' : ''}" id="stage-${i}">${s}</span>`
    ).join('');
}

function hideCrackProgress() {
    const status = document.getElementById('crack-progress-status');
    status.textContent = 'done';
    status.className = 'progress-status done';
    document.getElementById('crack-progress-bar').style.width = '100%';
    if (crackPollId) { clearInterval(crackPollId); crackPollId = null; }
}

function startCrackPolling() {
    let pollCount = 0;
    crackPollId = setInterval(async () => {
        pollCount++;
        // Update progress bar (animated estimate)
        const pct = Math.min(10 + pollCount * 3, 90);
        document.getElementById('crack-progress-bar').style.width = pct + '%';

        try {
            const log = await apiFetch('/api/log', 'GET');
            const recent = log.slice(-5);
            for (const entry of recent) {
                if (entry.action.includes('crack') || entry.action.includes('smart')) {
                    if (entry.status === 'done') {
                        const result = entry.result || {};
                        if (result.found || result.success) {
                            crackLog('🔑 CRACKED! Check Loot tab for results.');
                            showToast('🔑 Key cracked! Check Loot tab.', 'success');
                            const status = document.getElementById('crack-progress-status');
                            status.textContent = 'cracked!';
                            status.className = 'progress-status done';
                        } else {
                            crackLog('🔒 All strategies exhausted — key not in wordlist.');
                            const status = document.getElementById('crack-progress-status');
                            status.textContent = 'exhausted';
                            status.className = 'progress-status failed';
                        }
                        document.getElementById('crack-progress-bar').style.width = '100%';
                        clearInterval(crackPollId);
                        crackPollId = null;
                        return;
                    }
                }
            }
        } catch (_) {}

        // Auto-stop after 5 minutes
        if (pollCount > 100) {
            crackLog('[TIMEOUT] Monitoring stopped — check Log tab for final status.');
            hideCrackProgress();
        }
    }, 3000);
}

/* ── Loot ──────────────────────────────────────────────────── */

async function refreshLoot() {
    try {
        const data = await apiFetch('/api/loot', 'GET');
        const el = document.getElementById('loot-content');

        if (!data.keys || data.keys.length === 0) {
            el.innerHTML = `
                <div class="loot-empty">
                    <div class="loot-empty-icon">🔑</div>
                    <div class="loot-empty-text">No cracked keys yet</div>
                    <div class="loot-empty-hint">Use the Crack or Wi-Fi tab to crack passwords</div>
                </div>`;
            return;
        }

        let html = `<div class="loot-summary">
            <span class="loot-count">${data.cracked_count}</span>
            <span>credential${data.cracked_count !== 1 ? 's' : ''} cracked</span>
        </div>
        <div class="loot-grid">`;

        for (const key of data.keys) {
            const when = key.when ? key.when.substring(0, 19).replace('T', ' ') : 'unknown';
            html += `
                <div class="loot-card">
                    <div class="loot-essid">${esc(key.essid || key.id)}</div>
                    <div class="loot-id">${esc(key.id)}</div>
                    <div class="loot-key-row">
                        <span class="loot-key-label">KEY</span>
                        <span class="loot-key-value">${esc(key.key)}</span>
                    </div>
                    <div class="loot-meta">
                        <span class="loot-method">${esc(key.method)}</span>
                        <span class="loot-time">${when}</span>
                    </div>
                </div>`;
        }
        html += '</div>';
        el.innerHTML = html;
        // Update badge
        const badge = document.getElementById('loot-badge');
        if (badge) {
            badge.textContent = data.cracked_count;
            badge.style.display = data.cracked_count > 0 ? 'inline-block' : 'none';
        }
    } catch (e) {
        document.getElementById('loot-content').innerHTML =
            `<p class="placeholder-text">Error: ${e.message}</p>`;
    }
}

function exportLoot() {
    apiFetch('/api/loot', 'GET').then(data => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'james_loot.json';
        a.click();
    });
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
    const activeTab = document.querySelector('.tab.active');
    if (activeTab && activeTab.dataset.tab === tabId) return;

    if (activeTab) {
        activeTab.classList.remove('active');
        const activePanel = document.getElementById(`panel-${activeTab.dataset.tab}`);
        if (activePanel) {
            activePanel.classList.add('hidden');
            activePanel.classList.remove('active');
        }
    }

    const newTab = document.querySelector(`.tab[data-tab="${tabId}"]`);
    if (newTab) newTab.classList.add('active');

    const newPanel = document.getElementById(`panel-${tabId}`);
    if (newPanel) {
        newPanel.classList.remove('hidden');
        newPanel.classList.add('active');
    }

    // Auto-load data when switching to certain tabs
    if (tabId === 'loot') refreshLoot();
    if (tabId === 'log') refreshLog();
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
    if (el) el.textContent = new Date().toLocaleTimeString();
    setInterval(() => {
        if (el) el.textContent = new Date().toLocaleTimeString();
    }, 1000);
}

/* ── Toast Notifications ───────────────────────────────────── */

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

/* ── Quick Command Chips ───────────────────────────────────── */

function quickCmd(msg) {
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();
    const input = document.getElementById('chat-input');
    input.value = msg;
    sendChat();
}

/* ── System Stats ──────────────────────────────────────────── */

async function updateSystemStats() {
    try {
        const log = await apiFetch('/api/log', 'GET');
        const el = document.getElementById('stat-tasks');
        if (el) el.textContent = `${log.length} task${log.length !== 1 ? 's' : ''}`;
    } catch (_) {}
    try {
        const loot = await apiFetch('/api/loot', 'GET');
        const badge = document.getElementById('loot-badge');
        if (badge && loot.cracked_count > 0) {
            badge.textContent = loot.cracked_count;
            badge.style.display = 'inline-block';
        }
    } catch (_) {}
}

/* ── Clear Log View ────────────────────────────────────────── */

function clearLogView() {
    const el = document.getElementById('log-entries');
    if (el) el.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-title">View Cleared</div><div class="empty-desc">Click Refresh to reload</div></div>';
}

/* ── Background Particles ──────────────────────────────────── */

function initBackground() {
    const canvas = document.getElementById('bg-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w, h, particles = [];

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < 40; i++) {
        particles.push({
            x: Math.random() * w,
            y: Math.random() * h,
            r: Math.random() * 1.5 + 0.5,
            dx: (Math.random() - 0.5) * 0.3,
            dy: (Math.random() - 0.5) * 0.3,
            o: Math.random() * 0.3 + 0.05,
        });
    }

    function draw() {
        ctx.clearRect(0, 0, w, h);
        for (const p of particles) {
            p.x += p.dx;
            p.y += p.dy;
            if (p.x < 0) p.x = w;
            if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h;
            if (p.y > h) p.y = 0;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 240, 255, ${p.o})`;
            ctx.fill();
        }
        // draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(0, 240, 255, ${0.06 * (1 - dist / 120)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }
        requestAnimationFrame(draw);
    }
    draw();
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
