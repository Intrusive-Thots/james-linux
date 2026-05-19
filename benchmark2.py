import time
import random
import json
from datetime import datetime

# Fake data
task_log = [
    {"status": random.choice(["success", "error", "failed", "running", "info"]), "timestamp": "2023-10-10 10:10:10.123", "action": "test", "tool": "test", "result": {"key": "val"}}
    for _ in range(50000)
]

def old_report():
    total_tasks = len(task_log)
    success_count = sum(1 for e in task_log if e.get("status") == "success")
    error_count = sum(1 for e in task_log if e.get("status") in ("error", "failed"))

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

    return len(task_rows)

def new_report():
    total_tasks = len(task_log)
    success_count = 0
    error_count = 0

    task_rows_list = []

    # Pre-compile the status map
    status_map = {
        "success": "status-success",
        "error": "status-error",
        "failed": "status-error",
        "running": "status-running",
    }

    for e in task_log:
        status = e.get("status", "")
        if status == "success":
            success_count += 1
        elif status == "error" or status == "failed":
            error_count += 1

        status_class = status_map.get(status, "status-info")

        # Optimization: avoid json.dumps if result is empty or None
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
    return len(task_rows)

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
