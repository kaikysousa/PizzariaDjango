"""Gate: cancelar a impressão não apaga o carrinho."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
template = (ROOT / "templates" / "pedidos" / "recibo.html").read_text(encoding="utf-8")
css = (ROOT / "static" / "css" / "recibo.css").read_text(encoding="utf-8")

errors = []
if "localStorage.clear" in template:
    errors.append("recibo.html ainda usa localStorage.clear")
if "removeItem" not in template:
    errors.append("recibo.html não limpa apenas a chave do carrinho no novo pedido")
if "window.print()" not in template:
    errors.append("recibo.html sem botão de impressão")
if "@page" not in css:
    errors.append("recibo.css sem @page")
if "80mm" not in css:
    errors.append("recibo.css sem largura de 80mm")
if "margin: 0" not in css:
    errors.append("recibo.css sem margem zero")

if errors:
    for error in errors:
        print(f"FAIL: {error}")
    sys.exit(1)

print("GATE_PRINT_SAFETY ok")
