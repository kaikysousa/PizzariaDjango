"""Coleta condominios de Valparaiso de Goias para revisao manual.

Uso:
    python scripts/coletar_condominios.py --fonte tudo
    python scripts/coletar_condominios.py --fonte cnpj
    python scripts/coletar_condominios.py --fonte osm

O CNPJ vem dos Dados Abertos da Receita Federal. O OSM vem do Overpass.
O Google Maps nao e usado por codigo.
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from enderecos.coleta import escrever_csv  # noqa: E402
from enderecos.coleta_cnpj import (  # noqa: E402
    CNAE_PADRAO,
    MUNICIPIO_PADRAO,
    UF_PADRAO,
    coletar_cnpj,
)
from enderecos.coleta_merge import (  # noqa: E402
    mesclar,
    separar_pendencias,
)
from enderecos.coleta_osm import (  # noqa: E402
    BBOX_VALPARAISO,
    CIDADE_PADRAO,
    coletar_osm,
)


def _partes(valor):
    if "-" in valor:
        inicio, fim = valor.split("-", 1)
        return range(int(inicio), int(fim) + 1)
    return [int(parte) for parte in valor.split(",") if parte.strip()]


def _argumentos(argv=None):
    parser = argparse.ArgumentParser(
        description="Coleta condominios para o CSV de revisao."
    )
    parser.add_argument(
        "--fonte",
        choices=("cnpj", "osm", "tudo"),
        default="tudo",
    )
    parser.add_argument("--saida-dir", default="dados")
    parser.add_argument("--cache-dir", default=".cache-cnpj")
    parser.add_argument("--uf", default=UF_PADRAO)
    parser.add_argument("--municipio", default=MUNICIPIO_PADRAO)
    parser.add_argument("--cnae", default=CNAE_PADRAO)
    parser.add_argument("--cidade", default=CIDADE_PADRAO)
    parser.add_argument("--bbox", default=BBOX_VALPARAISO)
    parser.add_argument(
        "--url-base",
        default="https://dadosabertos.rfb.gov.br/CNPJ/",
        help="URL base dos Dados Abertos do CNPJ",
    )
    parser.add_argument(
        "--partes",
        default="0-9",
        help="Partes do CNPJ: 0-9, 0,3,5 etc.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = _argumentos(argv)
    saida = Path(args.saida_dir)
    saida.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache_dir)

    cnpj_csv = saida / "condominios-cnpj.csv"
    osm_csv = saida / "condominios-osm.csv"
    revisao_csv = saida / "condominios.csv"
    pendencias_csv = saida / "condominios-pendencias.csv"

    linhas = []
    if args.fonte in {"cnpj", "tudo"}:
        print("== CNPJ ==")
        cnpj = coletar_cnpj(
            cache,
            saida_csv=cnpj_csv,
            uf=args.uf,
            municipio=args.municipio,
            cnae=args.cnae,
            partes=_partes(args.partes),
            cidade=args.cidade,
            url_base=args.url_base,
        )
        linhas.extend(cnpj)
        print(f"cnpj: {len(cnpj)} linha(s)")

    osm = []
    if args.fonte in {"osm", "tudo"}:
        print("== OSM ==")
        try:
            osm = coletar_osm(
                saida_csv=osm_csv,
                bbox=args.bbox,
                cidade=args.cidade,
            )
        except RuntimeError as erro:
            print(f"aviso: OSM indisponivel ({erro})")
        else:
            linhas.extend(osm)
            print(f"osm: {len(osm)} linha(s)")

    if args.fonte == "tudo":
        mescladas = mesclar(linhas)
        validas, pendencias = separar_pendencias(mescladas)
        escrever_csv(validas, revisao_csv)
        escrever_csv(pendencias, pendencias_csv)
        print(
            "resumo: "
            f"total={len(mescladas)} "
            f"validas={len(validas)} "
            f"pendencias={len(pendencias)} "
            f"duplicados={len(linhas) - len(mescladas)}"
        )
        print(f"revisar: {revisao_csv}")
        print(f"pendencias: {pendencias_csv}")
    elif args.fonte == "cnpj":
        print(f"cnpj: {cnpj_csv}")
    else:
        print(f"osm: {osm_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
