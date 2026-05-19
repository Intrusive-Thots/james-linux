import time
import random
import json
from datetime import datetime
from james.core.report import generate_html_report

# Fake data
task_log = [
    {"status": random.choice(["success", "error", "failed", "running", "info"]), "timestamp": "2023-10-10 10:10:10.123", "action": "test", "tool": "test", "result": {"key": "val"}}
    for _ in range(50000)
]
context = {f"key{i}": f"val{i}" for i in range(100)}
loot_summary = {"cracked_count": 10, "cracked_networks": {f"essid{i}": {"key": "key", "method": "method", "date": "date"} for i in range(100)}}
tool_status = {f"tool{i}": random.choice([True, False]) for i in range(100)}
skills = ["skill1", "skill2"]
known_targets = {f"target{i}" for i in range(100)}

import gc
gc.disable()

# Old (Current)
runs = 10
old_times = []
for _ in range(runs):
    start = time.perf_counter()
    l1 = len(generate_html_report(task_log, context, loot_summary, tool_status, skills, known_targets))
    old_times.append(time.perf_counter() - start)

# Modified version
def generate_html_report_new(
    task_log: list[dict],
    context: dict,
    loot_summary: dict,
    tool_status: dict,
    skills: list[str],
    known_targets: set[str],
    wordlist_inventory: list[dict] | None = None,
) -> str:
    now = datetime.now()
    report_time = now.strftime("%Y-%m-%d %H:%M:%S")
    report_date = now.strftime("%B %d, %Y")

    # Stats
    total_tasks = len(task_log)
    success_count = 0
    error_count = 0
    tools_installed = sum(1 for v in tool_status.values() if v)
    tools_total = len(tool_status)
    cracked_count = loot_summary.get("cracked_count", 0)

    # Pre-compile the status map
    status_map = {
        "success": "status-success",
        "error": "status-error",
        "failed": "status-error",
        "running": "status-running",
    }

    # Build task rows
    task_rows_list = []

    for e in task_log:
        status = e.get("status", "")
        if status == "success":
            success_count += 1
        elif status == "error" or status == "failed":
            error_count += 1

        status_class = status_map.get(status, "status-info")
        result = e.get("result")
        result_json = json.dumps(result, default=str)[:200] if result else ""
        task_rows_list.append(f"""
            <tr>
                <td class="mono">{e.get('timestamp', '')[:19]}</td>
                <td>{e.get('action', '')}</td>
                <td><code>{e.get('tool', '')}</code></td>
                <td><span class="{status_class}">{status}</span></td>
                <td class="detail-cell">{result_json}</td>
            </tr>""")

    task_rows = "".join(task_rows_list)

    # Build tool grid
    tool_grid = "".join(
        f"<span class='tool-badge tool-ok'>✓ {tool}</span>\n" if is_installed else f"<span class='tool-badge tool-missing'>✗ {tool}</span>\n"
        for tool, is_installed in tool_status.items()
    )

    # Loot section
    loot_rows = "".join(
        f"<tr><td><code>{essid}</code></td><td class='key-value'>{info.get('key')}</td><td>{info.get('method')}</td><td class='mono'>{info.get('date')}</td></tr>\n"
        for essid, info in loot_summary.get("cracked_networks", {}).items()
    )

    # Target section
    target_list = "".join(f"<li><code>{t}</code></li>\n" for t in sorted(known_targets))

    # Context section
    context_rows = "".join(
        f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>\n"
        for k, v in context.items() if v
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JAMES Pentest Report — {report_date}</title>
<style>
    /* CSS omitted for brevity */
</style>
</head>
<body>
<div class="container">
    <div class="report-header">
        <h1>⚡ JAMES</h1>
        <div class="subtitle">PENETRATION TEST REPORT</div>
        <div class="date">{report_time}</div>
    </div>

    <!-- Stats Overview -->
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-value">{total_tasks}</div><div class="stat-label">Tasks Executed</div></div>
        <div class="stat-card success"><div class="stat-value">{success_count}</div><div class="stat-label">Successful</div></div>
        <div class="stat-card danger"><div class="stat-value">{error_count}</div><div class="stat-label">Errors</div></div>
        <div class="stat-card purple"><div class="stat-value">{cracked_count}</div><div class="stat-label">Keys Cracked</div></div>
        <div class="stat-card"><div class="stat-value">{len(known_targets)}</div><div class="stat-label">Targets Found</div></div>
        <div class="stat-card warn"><div class="stat-value">{tools_installed}/{tools_total}</div><div class="stat-label">Tools Installed</div></div>
    </div>

    <!-- Session Context -->
    {"" if not context_rows else f'''
    <div class="section">
        <div class="section-header">🎯 Session Context</div>
        <div class="section-body">
            <table>
                <tr><th>Variable</th><th>Value</th></tr>
                {context_rows}
            </table>
        </div>
    </div>
    '''}

    <!-- Known Targets -->
    {"" if not known_targets else f'''
    <div class="section">
        <div class="section-header">🎯 Discovered Targets ({len(known_targets)})</div>
        <div class="section-body">
            <ul class="target-grid">{target_list}</ul>
        </div>
    </div>
    '''}

    <!-- Cracked Keys -->
    {"" if cracked_count == 0 else f'''
    <div class="section">
        <div class="section-header">🔑 Cracked Credentials ({cracked_count})</div>
        <div class="section-body">
            <table>
                <tr><th>Target/ESSID</th><th>Key</th><th>Method</th><th>Date</th></tr>
                {loot_rows}
            </table>
        </div>
    </div>
    '''}

    <!-- Task Log -->
    <div class="section">
        <div class="section-header">📋 Task Log ({total_tasks} entries)</div>
        <div class="section-body">
            {"<p style='color:var(--text-dim)'>No tasks recorded in this session.</p>" if not task_rows else f'''
            <table>
                <tr><th>Timestamp</th><th>Action</th><th>Tool</th><th>Status</th><th>Details</th></tr>
                {task_rows}
            </table>
            '''}
        </div>
    </div>

    <!-- Tool Status -->
    <div class="section">
        <div class="section-header">⚙️ Tool Status ({tools_installed}/{tools_total} installed)</div>
        <div class="section-body">
            <div class="tools-grid">
                {tool_grid}
            </div>
        </div>
    </div>

    <div class="footer">
        Generated by JAMES Autonomous Pentesting Agent<br>
        {report_time} — {len(skills)} skills available
    </div>
</div>
</body>
</html>"""
    return html

new_times = []
for _ in range(runs):
    start = time.perf_counter()
    l2 = len(generate_html_report_new(task_log, context, loot_summary, tool_status, skills, known_targets))
    new_times.append(time.perf_counter() - start)

print(f"Old avg: {sum(old_times)/runs:.4f}s")
print(f"New avg: {sum(new_times)/runs:.4f}s")
print(f"Improvement: {(sum(old_times)/runs) / (sum(new_times)/runs):.2f}x faster")
