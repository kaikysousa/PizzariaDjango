"""Sobe um servidor temporário e roda o probe de UI como gate."""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
PORT = 8799
DB = Path(tempfile.gettempdir()) / "opencode" / "gate-ui.sqlite3"

env = dict(os.environ)
env["DJANGO_DB_PATH"] = str(DB)
env["DJANGO_DEBUG"] = "1"


def run(command, **kwargs):
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(f"FAIL: {' '.join(command)}")
    return result.stdout


DB.unlink(missing_ok=True)
run([PYTHON, "manage.py", "migrate", "--noinput"])
run([PYTHON, "scripts/seed_products.py"])

server = subprocess.Popen(
    [PYTHON, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"],
    cwd=ROOT,
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

try:
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.25)
    else:
        raise SystemExit("FAIL: servidor não subiu")

    result = subprocess.run(
        [
            PYTHON,
            "scripts/ui_probe.py",
            "--url",
            f"http://127.0.0.1:{PORT}/",
            "--label",
            "after",
            "--check",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    print(result.stdout[-4000:])
    if result.returncode != 0:
        print(result.stderr[-2000:])
        raise SystemExit("FAIL: probe de UI")
finally:
    server.terminate()
    try:
        server.wait(timeout=8)
    except Exception:
        server.kill()
    DB.unlink(missing_ok=True)

print("GATE_UI ok")
