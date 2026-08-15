"""
UrbanPulse Worker Launcher
==========================
Consolidated launcher for all background worker services.
Runs detection, dedup, scoring, routing, and notification workers
in a single process, reducing the number of terminal windows.

Usage:
    python services/worker_launcher.py
"""

import subprocess
import sys
import signal
import time
import os
from pathlib import Path

# Worker services to launch (relative to project root)
WORKERS = [
    {
        "name": "Detection Worker",
        "cwd": "services/detection-service",
        "cmd": [sys.executable, "-m", "app.main"],
    },
    {
        "name": "Dedup Worker",
        "cwd": "services/dedup-service",
        "cmd": [sys.executable, "-m", "app.main"],
    },
    {
        "name": "Scoring Worker",
        "cwd": "services/scoring-service",
        "cmd": [sys.executable, "-m", "app.main"],
    },
    {
        "name": "Routing Worker",
        "cwd": "services/routing-service",
        "cmd": [sys.executable, "-m", "app.main"],
    },
    {
        "name": "Notification Worker",
        "cwd": "services/notification-service",
        "cmd": [sys.executable, "-m", "app.main"],
    },
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
processes = []


def start_workers():
    """Launch all worker services as subprocesses."""
    print("=" * 60)
    print("  UrbanPulse Worker Launcher")
    print("=" * 60)

    for worker in WORKERS:
        cwd = PROJECT_ROOT / worker["cwd"]
        if not cwd.exists():
            print(f"  [SKIP] {worker['name']} — directory not found: {cwd}")
            continue

        try:
            proc = subprocess.Popen(
                worker["cmd"],
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            processes.append({"name": worker["name"], "proc": proc})
            print(f"  [OK]   {worker['name']} started (PID: {proc.pid})")
        except Exception as e:
            print(f"  [FAIL] {worker['name']} — {e}")

    print("=" * 60)
    print(f"  {len(processes)} workers running. Press Ctrl+C to stop all.")
    print("=" * 60)
    print()


def stream_output():
    """Stream worker output to console with prefixed labels."""
    import select
    import threading

    def stream_worker(name, proc):
        try:
            for line in iter(proc.stdout.readline, ""):
                if line:
                    print(f"  [{name}] {line.rstrip()}")
        except (ValueError, OSError):
            pass

    threads = []
    for worker in processes:
        t = threading.Thread(
            target=stream_worker,
            args=(worker["name"], worker["proc"]),
            daemon=True,
        )
        t.start()
        threads.append(t)

    return threads


def shutdown(signum=None, frame=None):
    """Gracefully terminate all worker processes."""
    print("\n  Shutting down workers...")
    for worker in processes:
        try:
            worker["proc"].terminate()
            worker["proc"].wait(timeout=5)
            print(f"  [STOP] {worker['name']} terminated")
        except subprocess.TimeoutExpired:
            worker["proc"].kill()
            print(f"  [KILL] {worker['name']} force-killed")
        except Exception:
            pass
    print("  All workers stopped.")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    start_workers()
    threads = stream_output()

    # Keep main thread alive
    try:
        while True:
            # Check if any worker died unexpectedly
            for worker in processes:
                if worker["proc"].poll() is not None:
                    print(f"  [WARN] {worker['name']} exited with code {worker['proc'].returncode}")
            time.sleep(5)
    except KeyboardInterrupt:
        shutdown()
