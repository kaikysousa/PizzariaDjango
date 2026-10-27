"""Semeia produtos de demonstração no banco apontado por DJANGO_DB_PATH."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoProject.settings")

import django  # noqa: E402

django.setup()

from pedidos.models import Produto  # noqa: E402

PRODUTOS = [
    ("Margherita", "45.90", "pizza", "Molho, mussarela e manjericão"),
    ("Calabresa", "49.90", "pizza", "Calabresa e cebola"),
    ("Quatro Queijos", "52.90", "pizza", "Mussarela, provolone, parmesão e gorgonzola"),
    ("Chocolate", "39.90", "pizza doce", "Chocolate ao leite"),
    ("Coca-Cola 2L", "12.00", "bebida", "Refrigerante"),
    ("Água Mineral", "5.00", "bebida", "500 ml"),
]

for nome, preco, categoria, descricao in PRODUTOS:
    Produto.objects.update_or_create(
        nome=nome,
        defaults={"preco": preco, "categoria": categoria, "descricao": descricao},
    )

print(f"SEED_OK produtos={Produto.objects.count()}")
