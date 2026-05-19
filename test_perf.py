import time
import random
import json
from datetime import datetime

def generate_html_report_old(
    task_log: list[dict],
    context: dict,
    loot_summary: dict,
    tool_status: dict,
    skills: list[str],
    known_targets: set[str],
    wordlist_inventory: list[dict] | None = None,
) -> str:
    # Stats
    total_tasks = len(task_log)
    success_count = sum(1 for e in task_log if e.get("status") == "success")
    error_count = sum(1 for e in task_log if e.get("status") in ("error", "failed"))

    # Build task rows
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
    return task_rows

def generate_html_report_new(
    task_log: list[dict],
    context: dict,
    loot_summary: dict,
    tool_status: dict,
    skills: list[str],
    known_targets: set[str],
    wordlist_inventory: list[dict] | None = None,
) -> str:
    # Stats
    total_tasks = len(task_log)
    success_count = 0
    error_count = 0

    # Build task rows
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
    return task_rows

# Create a dummy task log of 100,000 items
task_log = [{"status": random.choice(["success", "error", "failed", "running"])} for _ in range(100000)]

start = time.perf_counter()
generate_html_report_old(
    task_log=task_log,
    context={},
    loot_summary={},
    tool_status={},
    skills=[],
    known_targets=set(),
)
end_old = time.perf_counter()
time_old = end_old - start

start = time.perf_counter()
generate_html_report_new(
    task_log=task_log,
    context={},
    loot_summary={},
    tool_status={},
    skills=[],
    known_targets=set(),
)
end_new = time.perf_counter()
time_new = end_new - start

print(f"Old approach took: {time_old:.4f} seconds")
print(f"New approach took: {time_new:.4f} seconds")
