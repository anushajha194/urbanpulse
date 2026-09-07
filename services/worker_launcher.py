"""
UrbanPulse Worker Launcher
==========================
Consolidated launcher for all background worker services.

Each worker runs using its own service-specific virtual environment.
"""

import subprocess
import sys
import signal
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

WORKERS = [
    {
        "name": "Detection Worker",
        "service": "detection-service",
    },
    {
        "name": "Dedup Worker",
        "service": "dedup-service",
    },
    {
        "name": "Scoring Worker",
        "service": "scoring-service",
    },
    {
        "name": "Routing Worker",
        "service": "routing-service",
    },
    {
        "name": "Notification Worker",
        "service": "notification-service",
    },
]

processes = []


def get_python(service_dir):
    """Return the Python executable from the service's venv."""
    if sys.platform == "win32":
        python = service_dir / "venv" / "Scripts" / "python.exe"
    else:
        python = service_dir / "venv" / "bin" / "python"

    return python


def start_workers():
    """Launch all worker services."""
    print("=" * 60)
    print("  UrbanPulse Worker Launcher")
    print("=" * 60)

    for worker in WORKERS:
        service_dir = PROJECT_ROOT / "services" / worker["service"]
        python_exe = get_python(service_dir)

        if not service_dir.exists():
            print(
                f"  [SKIP] {worker['name']} — "
                f"directory not found: {service_dir}"
            )
            continue

        if not python_exe.exists():
            print(
                f"  [FAIL] {worker['name']} — "
                f"venv Python not found: {python_exe}"
            )
            continue

        cmd = [
            str(python_exe),
            "-m",
            "app.main",
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(service_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            processes.append({
                "name": worker["name"],
                "proc": proc,
            })

            print(
                f"  [OK]   {worker['name']} started "
                f"(PID: {proc.pid})"
            )
            print(
                f"         Python: {python_exe}"
            )

        except Exception as e:
            print(f"  [FAIL] {worker['name']} — {e}")

    print("=" * 60)
    print(
        f"  {len(processes)} workers running. "
        "Press Ctrl+C to stop all."
    )
    print("=" * 60)
    print()


def stream_output():
    """Stream worker output to console."""
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
        thread = threading.Thread(
            target=stream_worker,
            args=(worker["name"], worker["proc"]),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    return threads


def shutdown(signum=None, frame=None):
    """Gracefully stop all workers."""
    print("\n  Shutting down workers...")

    for worker in processes:
        proc = worker["proc"]

        try:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
                print(
                    f"  [STOP] {worker['name']} terminated"
                )
        except subprocess.TimeoutExpired:
            proc.kill()
            print(
                f"  [KILL] {worker['name']} force-killed"
            )
        except Exception:
            pass

    print("  All workers stopped.")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    start_workers()
    stream_output()

    reported_exits = set()

    try:
        while True:
            for worker in processes:
                proc = worker["proc"]

                if proc.poll() is not None and proc.pid not in reported_exits:
                    reported_exits.add(proc.pid)
                    print(
                        f"  [WARN] {worker['name']} "
                        f"exited with code {proc.returncode}"
                    )

            time.sleep(5)

    except KeyboardInterrupt:
        shutdown()