"""Gate: `check --deploy` sem W009 e W018 em modo produção."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
python = sys.executable

env = dict(os.environ)
env.update(
    {
        "DJANGO_DEBUG": "0",
        "DJANGO_SECRET_KEY": "gate-only-secret-key-with-more-than-fifty-characters-1234567890",
        "DJANGO_ALLOWED_HOSTS": "example.com",
        "DJANGO_SECURE_SSL_REDIRECT": "1",
    }
)

result = subprocess.run(
    [python, "manage.py", "check", "--deploy"],
    cwd=ROOT,
    capture_output=True,
    text=True,
    env=env,
)
output = (result.stdout or "") + (result.stderr or "")
print(output.strip())

for code in ("security.W009", "security.W018"):
    if code in output:
        print(f"FAIL: {code} ainda presente")
        sys.exit(1)

if result.returncode != 0:
    print("FAIL: check --deploy saiu com erro")
    sys.exit(1)

print("GATE_DEPLOY ok")
