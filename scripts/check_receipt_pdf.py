"""Gate: imprime o recibo real em PDF e mede a largura de 80 mm."""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
PORT = 8798
DEBUG_PORT = 9334
DB = Path(tempfile.gettempdir()) / "opencode" / "gate-receipt.sqlite3"
PDF = Path(tempfile.gettempdir()) / "opencode" / "gate-receipt.pdf"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME):
    CHROME = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

env = dict(os.environ)
env["DJANGO_DB_PATH"] = str(DB)
env["DJANGO_DEBUG"] = "1"


def run(command):
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(f"FAIL: {' '.join(command)}")
    return result.stdout


DB.unlink(missing_ok=True)
PDF.unlink(missing_ok=True)
run([PYTHON, "manage.py", "migrate", "--noinput"])
seed = run([PYTHON, "manage.py", "seed_demo"])
match = re.search(r"SEED_DEMO_TOKEN=([0-9a-f-]{36})", seed)
if not match:
    raise SystemExit("FAIL: seed_demo nÃ£o devolveu token")
token = match.group(1)

server = subprocess.Popen(
    [PYTHON, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"],
    cwd=ROOT,
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

profile = tempfile.mkdtemp(prefix="receipt-pdf-")
chrome = subprocess.Popen(
    [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile}",
        "about:blank",
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)


def wait_json(url, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return json.load(response)
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"timeout: {url}")


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60)
        self.seq = 0

    def call(self, method, **params):
        self.seq += 1
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self.seq:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message.get("result", {})


try:
    wait_json(f"http://127.0.0.1:{DEBUG_PORT}/json/version")
    request = urllib.request.Request(
        f"http://127.0.0.1:{DEBUG_PORT}/json/new?about:blank", method="PUT"
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        target = json.load(response)

    cdp = CDP(target["webSocketDebuggerUrl"])
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")

    url = f"http://127.0.0.1:{PORT}/pedido/{token}/recibo/"
    cdp.call("Page.navigate", url=url)
    time.sleep(1.0)
    for _ in range(100):
        time.sleep(0.1)
        ready = cdp.call(
            "Runtime.evaluate",
            expression="document.readyState",
            returnByValue=True,
        )
        if ready.get("result", {}).get("value") == "complete":
            break

    pdf_data = cdp.call(
        "Page.printToPDF", printBackground=True, preferCSSPageSize=True
    )["data"]
    PDF.write_bytes(base64.b64decode(pdf_data))

    reader = PdfReader(str(PDF))
    page = reader.pages[0]
    width_mm = float(page.mediabox.width) / 72 * 25.4
    text = page.extract_text() or ""

    print(f"largura={width_mm:.1f}mm paginas={len(reader.pages)}")
    if abs(width_mm - 80) > 1.5:
        raise SystemExit(f"FAIL: largura {width_mm:.1f}mm, esperado 80mm")
    if "Margherita" not in text or "Calabresa" not in text:
        raise SystemExit("FAIL: itens ausentes no PDF")
    if "Total" not in text:
        raise SystemExit("FAIL: total ausente no PDF")
finally:
    for process in (chrome, server):
        process.terminate()
        try:
            process.wait(timeout=8)
        except Exception:
            process.kill()
    shutil.rmtree(profile, ignore_errors=True)
    DB.unlink(missing_ok=True)

print("GATE_RECEIPT_80MM ok")

