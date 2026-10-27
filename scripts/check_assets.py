"""Gate: artefatos de design, motion acessível e capturas existem."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMP = Path(__file__).resolve().parent.parent / ".tmp"
SHOTS = Path.home() / "AppData" / "Local" / "Temp" / "opencode" / "shots"

required_files = [
    ROOT / "DESIGN.md",
    ROOT / "AUDITORIA-COMPLEMENTAR.md",
    ROOT / "static" / "css" / "tokens.css",
    ROOT / "static" / "css" / "estilos.css",
    ROOT / "static" / "js" / "motion.js",
    ROOT / "static" / "js" / "carrinho.js",
]
errors = [f"arquivo ausente: {path.relative_to(ROOT)}" for path in required_files if not path.exists()]

if not errors:
    design = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
    for secao in ("## Tokens", "## Tipografia", "## Componentes", "## Motion", "## Acessibilidade"):
        if secao not in design:
            errors.append(f"DESIGN.md sem seção {secao}")

    estilos = (ROOT / "static" / "css" / "estilos.css").read_text(encoding="utf-8")
    if "prefers-reduced-motion" not in estilos:
        errors.append("estilos.css sem prefers-reduced-motion")
    if "data-reveal" not in estilos:
        errors.append("estilos.css sem reveal de entrada")

    motion = (ROOT / "static" / "js" / "motion.js").read_text(encoding="utf-8")
    if "IntersectionObserver" not in motion:
        errors.append("motion.js sem IntersectionObserver")
    if "prefers-reduced-motion" not in motion:
        errors.append("motion.js ignora prefers-reduced-motion")

    carrinho = (ROOT / "static" / "js" / "carrinho.js").read_text(encoding="utf-8")
    if "carrinho:v2" not in carrinho:
        errors.append("carrinho.js sem chave de armazenamento")
    if "adicionar" not in carrinho or "remover" not in carrinho:
        errors.append("carrinho.js sem adicionar/remover")

for width in (390, 768, 1280):
    shot = SHOTS / f"after-{width}.png"
    if not shot.exists():
        errors.append(f"captura ausente: {shot}")

ignored = subprocess.run(
    ["git", "check-ignore", "-q", ".firecrawl"],
    cwd=ROOT,
)
if ignored.returncode != 0:
    errors.append(".firecrawl não está no .gitignore")

if errors:
    for error in errors:
        print(f"FAIL: {error}")
    sys.exit(1)

print("GATE_ASSETS ok")
