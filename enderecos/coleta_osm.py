"""Coleta de condominios no OpenStreetMap via Overpass."""

import json
import re
import time
import urllib.parse
import urllib.request

from .coleta import (
    capitalizar_texto,
    escrever_csv,
    formatar_cep,
    normalizar_espacos,
    sem_acento,
)

BBOX_VALPARAISO = "-16.12,-48.03,-16.01,-47.92"
USER_AGENT = "PizzariaDjango/1.0 (coleta de condominios)"
CIDADE_PADRAO = "Valparaíso de Goiás"
ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
CONSULTA = """
[out:json][timeout:{timeout}];
(
  nwr["landuse"="residential"]({bbox});
  nwr["building"="residential"]({bbox});
  nwr["name"~"Residencial|Condom[ií]nio|Colinas|Jardim|Parque|Vila|Conjunto",i]({bbox});
);
out center tags 2000;
"""
_GENERICOS = {"residencial", "condominio", "condominio residencial", "edificio"}
_RELEVANTE = re.compile(
    r"condominio|residencial|colinas|ville|village|club",
    re.IGNORECASE,
)
_POI_TAGS = ("shop", "amenity", "office", "tourism", "leisure")


def _limitar(valor, tamanho):
    return normalizar_espacos(valor)[:tamanho]


def _nome_generico(nome):
    return sem_acento(nome).lower() in _GENERICOS


def _relevante(nome, tags):
    """Mantem condominios por nome ou por endereco completo."""
    if any(tag in tags for tag in _POI_TAGS):
        return False
    if _RELEVANTE.search(sem_acento(nome)):
        return True
    return bool(tags.get("addr:street") and tags.get("addr:suburb"))


def extrair_condominios(dados, cidade=CIDADE_PADRAO):
    """Converte a resposta do Overpass em linhas do CSV de revisao."""
    linhas = []
    for elemento in dados.get("elements") or []:
        tags = elemento.get("tags") or {}
        nome = normalizar_espacos(tags.get("name", ""))
        if not nome or _nome_generico(nome):
            continue
        if not _relevante(nome, tags):
            continue

        linhas.append(
            {
                "nome": _limitar(capitalizar_texto(nome), 120),
                "endereco": _limitar(
                    capitalizar_texto(tags.get("addr:street", "")), 150
                ),
                "numero": _limitar(tags.get("addr:housenumber", ""), 20),
                "bairro": _limitar(
                    capitalizar_texto(tags.get("addr:suburb", "")), 80
                ),
                "cidade": _limitar(
                    capitalizar_texto(tags.get("addr:city", "")) or cidade,
                    80,
                ),
                "cep": formatar_cep(tags.get("addr:postcode", ""))[:9],
                "referencia": f"osm:{elemento.get('type')}/{elemento.get('id')}",
                "ativo": "sim",
                "revisado": "nao",
                "fonte": "osm",
                "nome_origem": _limitar(nome, 120),
                "cnpj": "",
            }
        )
    return linhas


def consultar_overpass(bbox=BBOX_VALPARAISO, timeout=120, log=print):
    """Consulta o Overpass com retry e endpoints alternativos."""
    consulta = CONSULTA.format(bbox=bbox, timeout=timeout)
    dados = urllib.parse.urlencode({"data": consulta}).encode()
    ultimo_erro = None
    for endpoint in ENDPOINTS:
        for tentativa in range(1, 4):
            try:
                log(f"osm: {endpoint} (tentativa {tentativa})")
                requisicao = urllib.request.Request(
                    endpoint,
                    data=dados,
                    headers={"User-Agent": USER_AGENT},
                )
                with urllib.request.urlopen(
                    requisicao, timeout=timeout + 30
                ) as resposta:
                    return json.load(resposta)
            except Exception as falha:  # noqa: BLE001 - retry de rede
                ultimo_erro = falha
                log(f"osm falhou: {falha}")
                time.sleep(5 * tentativa)
    raise RuntimeError(f"Overpass indisponivel: {ultimo_erro}")


def coletar_osm(
    saida_csv=None,
    bbox=BBOX_VALPARAISO,
    cidade=CIDADE_PADRAO,
    log=print,
):
    dados = consultar_overpass(bbox=bbox, log=log)
    linhas = extrair_condominios(dados, cidade)
    if saida_csv is not None:
        escrever_csv(linhas, saida_csv)
        log(f"csv: {saida_csv} ({len(linhas)} linhas)")
    return linhas
