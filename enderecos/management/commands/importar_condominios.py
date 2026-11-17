"""Importa condominios de um CSV revisado, sem sobrescrever cadastro manual."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from enderecos.coleta import chave_dedup, ler_csv, valor_revisado
from enderecos.models import Condominio

OBRIGATORIOS = ("nome", "endereco", "bairro", "cidade")


class Command(BaseCommand):
    help = "Importa condominios de um CSV revisado (create-only)."

    def add_arguments(self, parser):
        parser.add_argument("csv", help="Caminho do CSV de revisao")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o resumo sem gravar",
        )
        parser.add_argument(
            "--incluir-nao-revisados",
            action="store_true",
            help="Importa tambem linhas com revisado=nao",
        )

    def handle(self, *args, **options):
        caminho = options["csv"]
        try:
            linhas = ler_csv(caminho)
        except FileNotFoundError as erro:
            raise CommandError(f"CSV nao encontrado: {caminho}") from erro

        existentes = {
            chave_dedup(
                condominio.nome,
                condominio.endereco,
                condominio.numero,
                condominio.bairro,
            ): condominio
            for condominio in Condominio.objects.all()
        }
        criados = 0
        repetidos = 0
        ignorados = 0
        pendencias = 0

        with transaction.atomic():
            for linha in linhas:
                revisado = valor_revisado(linha.get("revisado", ""))
                if (
                    not options["incluir_nao_revisados"]
                    and not revisado
                ):
                    ignorados += 1
                    continue

                valores = {
                    campo: (linha.get(campo) or "").strip()
                    for campo in OBRIGATORIOS
                }
                if not all(valores.values()):
                    pendencias += 1
                    continue

                chave = chave_dedup(
                    valores["nome"],
                    valores["endereco"],
                    (linha.get("numero") or "").strip(),
                    valores["bairro"],
                )
                if chave in existentes:
                    repetidos += 1
                    continue

                existentes[chave] = None
                criados += 1
                if options["dry_run"]:
                    continue

                Condominio.objects.create(
                    nome=valores["nome"][:120],
                    endereco=valores["endereco"][:150],
                    numero=(linha.get("numero") or "").strip()[:20],
                    bairro=valores["bairro"][:80],
                    cidade=valores["cidade"][:80],
                    cep=(linha.get("cep") or "").strip()[:9],
                    referencia=(linha.get("referencia") or "").strip()[:150],
                    ativo=valor_revisado(
                        linha.get("ativo") or "sim"
                    ),
                )

        self.stdout.write(
            "criados={} existentes={} ignorados={} pendencias={}".format(
                criados, repetidos, ignorados, pendencias
            )
        )
