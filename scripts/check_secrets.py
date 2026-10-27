"""Gate: nenhum segredo versionado na branch."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {
    ".py", ".html", ".css", ".js", ".json", ".jsonc", ".md", ".txt",
    ".cfg", ".ini", ".toml", ".yml", ".yaml", ".env", ".example",
}
SKIP = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "AUDITORIA.md",
    "AUDITORIA-COMPLEMENTAR.md", "RELATORIO-CORRECAO.md",
}

PATTERNS = [
    re.compile(r"django-insecure-[A-Za-z0-9_!@#$%^&*()\-+=]{20,}"),
    re.compile(r"SECRET_KEY\s*=\s*['\"][A-Za-z0-9_!@#$%^&*()\-+=]{30,}['\"]"),
    re.compile(r"fc-[a-f0-9]{24,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
]

tracked = subprocess.run(
    ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
).stdout.splitlines()

findings = []
for relative in tracked:
    if relative in SKIP:
        continue
    path = ROOT / relative
    if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for pattern in PATTERNS:
        if pattern.search(text):
            findings.append(f"{relative}: {pattern.pattern}")
            break

if findings:
    for finding in findings:
        print(f"FAIL: {finding}")
    sys.exit(1)

print("GATE_SECRETS ok")
