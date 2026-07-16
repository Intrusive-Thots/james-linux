import time
from pathlib import Path
import tempfile
import os

def test_original(files):
    start = time.time()
    for f in files:
        if f.stat().st_size < 2:
            continue
        try:
            mtime = f.stat().st_mtime
        except Exception:
            mtime = 0
        cache_key = f"{f}_{mtime}"
        try:
            lines = max(1, f.stat().st_size // 10)
        except Exception:
            lines = 0
    return time.time() - start

def test_optimized(files):
    start = time.time()
    for f in files:
        f_stat = f.stat()
        if f_stat.st_size < 2:
            continue
        try:
            mtime = f_stat.st_mtime
        except Exception:
            mtime = 0
        cache_key = f"{f}_{mtime}"
        try:
            lines = max(1, f_stat.st_size // 10)
        except Exception:
            lines = 0
    return time.time() - start

with tempfile.TemporaryDirectory() as d:
    dir_path = Path(d)
    files = []
    for i in range(1000):
        p = dir_path / f"{i}.txt"
        p.write_text("hello world")
        files.append(p)

    # Warmup
    test_original(files)
    test_optimized(files)

    orig_time = sum(test_original(files) for _ in range(10))
    opt_time = sum(test_optimized(files) for _ in range(10))

    print(f"Original: {orig_time:.4f}s")
    print(f"Optimized: {opt_time:.4f}s")
    print(f"Improvement: {(orig_time - opt_time) / orig_time * 100:.2f}%")
