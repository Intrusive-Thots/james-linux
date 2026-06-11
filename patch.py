with open("james/web/app.js", "r") as f:
    content = f.read()

old_code = """/* ── Tab Switching ─────────────────────────────────────────── */

function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => { p.classList.add('hidden'); p.classList.remove('active'); });
    document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');
    const panel = document.getElementById(`panel-${tabId}`);
    panel.classList.remove('hidden');
    panel.classList.add('active');

    // Auto-load data when switching to certain tabs
    if (tabId === 'loot') refreshLoot();
    if (tabId === 'log') refreshLog();
}"""

new_code = """/* ── Tab Switching ─────────────────────────────────────────── */

let activeTabEl = null;
let activePanelEl = null;

function switchTab(tabId) {
    if (activeTabEl) {
        activeTabEl.classList.remove('active');
    } else {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    }

    if (activePanelEl) {
        activePanelEl.classList.add('hidden');
        activePanelEl.classList.remove('active');
    } else {
        document.querySelectorAll('.panel').forEach(p => { p.classList.add('hidden'); p.classList.remove('active'); });
    }

    const tabEl = document.querySelector(`.tab[data-tab="${tabId}"]`);
    const panel = document.getElementById(`panel-${tabId}`);

    activeTabEl = tabEl;
    activePanelEl = panel;

    if (tabEl) tabEl.classList.add('active');
    if (panel) {
        panel.classList.remove('hidden');
        panel.classList.add('active');
    }

    // Auto-load data when switching to certain tabs
    if (tabId === 'loot') refreshLoot();
    if (tabId === 'log') refreshLog();
}"""

content = content.replace(old_code, new_code)

with open("james/web/app.js", "w") as f:
    f.write(content)
