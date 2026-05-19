import time
import random
import json
from datetime import datetime

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

def old_report():
    total_tasks = len(task_log)
    success_count = sum(1 for e in task_log if e.get("status") == "success")
    error_count = sum(1 for e in task_log if e.get("status") in ("error", "failed"))
    tools_installed = sum(1 for v in tool_status.values() if v)
    tools_total = len(tool_status)
    cracked_count = loot_summary.get("cracked_count", 0)

    task_rows = ""
    for e in task_log:
        status_class = {
            "success": "status-success",
            "error": "status-error",
            "failed": "status-error",
            "running": "status-running",
        }.get(e.get("status", ""), "status-info")
        result_json = json.dumps(e.get("result", {}), default=str)[:200] if e.get("result") else ""
        task_rows += f"""
            <tr>
                <td class="mono">{e.get('timestamp', '')[:19]}</td>
                <td>{e.get('action', '')}</td>
                <td><code>{e.get('tool', '')}</code></td>
                <td><span class="{status_class}">{e.get('status', '')}</span></td>
                <td class="detail-cell">{result_json}</td>
            </tr>"""

    tool_grid = ""
    for tool, is_installed in tool_status.items():
        if is_installed:
            tool_grid += f"<span class='tool-badge tool-ok'>✓ {tool}</span>\n"
        else:
            tool_grid += f"<span class='tool-badge tool-missing'>✗ {tool}</span>\n"

    loot_rows = ""
    for essid, info in loot_summary.get("cracked_networks", {}).items():
        loot_rows += f"<tr><td><code>{essid}</code></td><td class='key-value'>{info.get('key')}</td><td>{info.get('method')}</td><td class='mono'>{info.get('date')}</td></tr>\n"

    target_list = ""
    for t in sorted(known_targets):
        target_list += f"<li><code>{t}</code></li>\n"

    context_rows = ""
    for k, v in context.items():
        if v:
            context_rows += f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>\n"

    return len(task_rows) + len(tool_grid) + len(loot_rows) + len(target_list) + len(context_rows)


def new_report():
    total_tasks = len(task_log)
    success_count = 0
    error_count = 0
    tools_installed = sum(1 for v in tool_status.values() if v)
    tools_total = len(tool_status)
    cracked_count = loot_summary.get("cracked_count", 0)

    task_rows_list = []
    for e in task_log:
        status = e.get("status", "")
        if status == "success":
            success_count += 1
        elif status in ("error", "failed"):
            error_count += 1

        status_class = {
            "success": "status-success",
            "error": "status-error",
            "failed": "status-error",
            "running": "status-running",
        }.get(status, "status-info")
        result_json = json.dumps(e.get("result", {}), default=str)[:200] if e.get("result") else ""
        task_rows_list.append(f"""
            <tr>
                <td class="mono">{e.get('timestamp', '')[:19]}</td>
                <td>{e.get('action', '')}</td>
                <td><code>{e.get('tool', '')}</code></td>
                <td><span class="{status_class}">{status}</span></td>
                <td class="detail-cell">{result_json}</td>
            </tr>""")
    task_rows = "".join(task_rows_list)

    tool_grid = "".join(
        f"<span class='tool-badge tool-ok'>✓ {tool}</span>\n" if is_installed else f"<span class='tool-badge tool-missing'>✗ {tool}</span>\n"
        for tool, is_installed in tool_status.items()
    )

    loot_rows = "".join(
        f"<tr><td><code>{essid}</code></td><td class='key-value'>{info.get('key')}</td><td>{info.get('method')}</td><td class='mono'>{info.get('date')}</td></tr>\n"
        for essid, info in loot_summary.get("cracked_networks", {}).items()
    )

    target_list = "".join(f"<li><code>{t}</code></li>\n" for t in sorted(known_targets))

    context_rows = "".join(
        f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>\n"
        for k, v in context.items() if v
    )

    return len(task_rows) + len(tool_grid) + len(loot_rows) + len(target_list) + len(context_rows)

import gc
gc.disable()

# Warmup
old_report()
new_report()

runs = 5
old_times = []
for _ in range(runs):
    start = time.perf_counter()
    l1 = old_report()
    old_times.append(time.perf_counter() - start)

new_times = []
for _ in range(runs):
    start = time.perf_counter()
    l2 = new_report()
    new_times.append(time.perf_counter() - start)

print(f"Output matched: {l1 == l2}")
print(f"Old avg: {sum(old_times)/runs:.4f}s")
print(f"New avg: {sum(new_times)/runs:.4f}s")
print(f"Improvement: {(sum(old_times)/runs) / (sum(new_times)/runs):.2f}x faster")
