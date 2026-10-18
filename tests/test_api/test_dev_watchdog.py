import os
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_worker_exits_when_dev_parent_dies():
    parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"])
    env = {**os.environ, "DEV_PARENT_PID": str(parent.pid), "PYTHONPATH": ROOT}
    worker = subprocess.Popen([sys.executable, "-c",
                               "import time; from interface.backend import dev_watchdog; dev_watchdog.start(); time.sleep(30)"],
                              env=env, cwd=ROOT)
    try:
        assert worker.wait(timeout=15) == 0
    finally:
        worker.kill()
        parent.kill()


def test_watchdog_noop_without_env(monkeypatch):
    from interface.backend import dev_watchdog
    monkeypatch.delenv("DEV_PARENT_PID", raising=False)
    dev_watchdog.start()
    assert not [t for t in threading.enumerate() if t.name == "dev-parent-watchdog"]
