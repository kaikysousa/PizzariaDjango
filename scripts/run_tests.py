"""Executa a suíte Django e imprime um token de sucesso decisivo."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
command = [sys.executable, "manage.py", "test", *sys.argv[1:]]
result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
output = (result.stdout or "") + (result.stderr or "")
print(output)

match = re.search(r"Ran (\d+) tests?", output)
if result.returncode != 0 or not match or int(match.group(1)) == 0:
    print("FAIL: testes não passaram ou a suíte está vazia")
    sys.exit(1)

print(f"GATE_TESTS_PASSED {match.group(1)}")
