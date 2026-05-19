import time
import random
import json

# Focus strictly on the logic from the issue description
def bench_old(task_log):
    total_tasks = len(task_log)
    success_count = sum(1 for e in task_log if e.get("status") == "success")
    error_count = sum(1 for e in task_log if e.get("status") in ("error", "failed"))
    return total_tasks, success_count, error_count

def bench_new(task_log):
    total_tasks = len(task_log)
    success_count = 0
    error_count = 0
    for e in task_log:
        status = e.get("status")
        if status == "success":
            success_count += 1
        elif status in ("error", "failed"):
            error_count += 1
    return total_tasks, success_count, error_count

task_log = [{"status": random.choice(["success", "error", "failed", "running", "info"])} for _ in range(1_000_000)]

# warmup
bench_old(task_log)
bench_new(task_log)

runs = 10

old_t = 0
for _ in range(runs):
    s = time.perf_counter()
    bench_old(task_log)
    old_t += time.perf_counter() - s

new_t = 0
for _ in range(runs):
    s = time.perf_counter()
    bench_new(task_log)
    new_t += time.perf_counter() - s

print(f"Old avg: {old_t/runs:.4f}s")
print(f"New avg: {new_t/runs:.4f}s")
print(f"Improvement: {old_t/new_t:.2f}x faster")
