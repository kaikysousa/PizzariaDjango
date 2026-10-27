"""Importa produtos de um CSV para o banco configurado.

Uso:
    python importar_produtos.py
    python importar_produtos.py --arquivo cardapio.csv
    python importar_produtos.py --dry-run
"""

import argparse
import csv
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def importar(caminho, dry_run=False):
    from decimal import Decimal, InvalidOperation

    from pedidos.models import Categoria, Produto

    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"CSV não encontrado: {caminho}")

    criados = 0
    with caminho.open(newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        obrigatorios = {"nome", "preco", "categoria"}
        if not leitor.fieldnames or not obrigatorios.issubset(set(leitor.fieldnames)):
            raise ValueError("CSV precisa das colunas nome, preco e categoria")

        for linha in leitor:
            numero = leitor.line_num
            nome = (linha.get("nome") or "").strip()
            if not nome:
                continue

            categoria = (linha.get("categoria") or "").strip().lower()
            if categoria not in Categoria.values:
                raise ValueError(
                    f"Linha {numero}: categoria inválida {categoria!r}"
                )

            bruto = (linha.get("preco") or "").replace(",", ".").strip()
            try:
                preco = Decimal(bruto)
            except (InvalidOperation, ValueError):
                raise ValueError(f"Linha {numero}: preço inválido {bruto!r}")
            if preco <= 0:
                raise ValueError(f"Linha {numero}: preço deve ser maior que zero")

            dados = {
                "preco": preco,
                "categoria": categoria,
                "descricao": (linha.get("descricao") or "").strip(),
            }

            if dry_run:
                print(f"DRY_RUN {nome} | {preco} | {categoria}")
            else:
                existente = Produto.objects.filter(nome__iexact=nome).first()
                if existente:
                    for campo, valor in dados.items():
                        setattr(existente, campo, valor)
                    existente.save(update_fields=list(dados))
                else:
                    Produto.objects.create(nome=nome, **dados)
            criados += 1

    return criados


def main(argv=None):
    parser = argparse.ArgumentParser(description="Importa produtos de um CSV.")
    parser.add_argument(
        "--arquivo",
        default=str(BASE_DIR / "cardapio.csv"),
        help="Caminho do CSV (padrão: cardapio.csv na raiz).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria importado sem gravar.",
    )
    args = parser.parse_args(argv)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoProject.settings")

    import django

    django.setup()

    try:
        total = importar(args.arquivo, dry_run=args.dry_run)
    except (FileNotFoundError, ValueError) as erro:
        print(f"IMPORT_ERROR {erro}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"IMPORT_DRY_RUN {total}")
    else:
        print(f"IMPORT_OK {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
