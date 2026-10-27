"""Gate: configuração de segurança sem segredos literais e sem junk versionado."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "DjangoProject" / "settings.py"
ENV_EXAMPLE = ROOT / ".env.example"
GITIGNORE = ROOT / ".gitignore"

errors = []


def fail(message):
    errors.append(message)


settings_text = SETTINGS.read_text(encoding="utf-8")
if "django-insecure-" in settings_text:
    fail("settings.py ainda contém a SECRET_KEY gerada pelo Django")
if "DJANGO_SECRET_KEY" not in settings_text:
    fail("settings.py não lê DJANGO_SECRET_KEY do ambiente")
if "DJANGO_DEBUG" not in settings_text:
    fail("settings.py não lê DJANGO_DEBUG do ambiente")
if re.search(r"SECRET_KEY\s*=\s*['\"][^'\"]{20,}['\"]", settings_text):
    fail("settings.py ainda tem SECRET_KEY literal")
if "34.39.141.209" in settings_text:
    fail("settings.py ainda fixa o IP de produção")
if re.search(r"^DEBUG\s*=\s*True\s*$", settings_text, re.MULTILINE):
    fail("settings.py ainda fixa DEBUG = True")

if not ENV_EXAMPLE.exists():
    fail(".env.example ausente")
else:
    env_text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for key in ("DJANGO_SECRET_KEY", "DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS"):
        if key not in env_text:
            fail(f".env.example sem {key}")

gitignore = GITIGNORE.read_text(encoding="utf-8")
for entry in ("GATES.md", ".unlazy/", "PROMPT-*.md", ".venv"):
    if entry not in gitignore:
        fail(f".gitignore sem {entry}")

tracked = subprocess.run(
    ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
).stdout.splitlines()
for forbidden in (".idea/", "gunicorn-error-log", "templates/pedidos/index.html.save"):
    if any(path == forbidden.rstrip("/") or path.startswith(forbidden) for path in tracked):
        fail(f"arquivo de lixo ainda versionado: {forbidden}")

if errors:
    for error in errors:
        print(f"FAIL: {error}")
    sys.exit(1)

print("GATE_SECURITY ok")
