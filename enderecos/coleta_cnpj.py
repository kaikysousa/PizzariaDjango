"""Coleta de condominios a partir dos Dados Abertos do CNPJ."""

import csv
import io
import re
import shutil
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .coleta import (
    capitalizar_texto,
    escrever_csv,
    formatar_cep,
    nome_para_exibicao,
    normalizar_espacos,
    sem_acento,
)

SHARE_URL = (
    "https://arquivos.receitafederal.gov.br/"
    "public.php/dav/files/YggdBLfdninEJX9/"
)
COMPETENCIA_PADRAO = "2026-11"
URL_BASE = SHARE_URL
USER_AGENT = "PizzariaDjango/1.0 (coleta de condominios)"
UF_PADRAO = "GO"
MUNICIPIO_PADRAO = "VALPARAISO DE GOIAS"
CIDADE_PADRAO = "Valparaíso de Goiás"
CNAE_PADRAO = "8112500"
SITUACAO_ATIVA = "02"


def _chave_texto(valor):
    return sem_acento(normalizar_espacos(valor)).upper()


def _competencias_de_xml(conteudo):
    """Extrai as pastas AAAA-MM de um PROPFIND do Nextcloud."""
    raiz = ET.fromstring(conteudo)
    competencias = set()
    for elemento in raiz.iter():
        if elemento.tag.endswith("href") and elemento.text:
            achado = re.search(r"/(\d{4}-\d{2})/?$", elemento.text)
            if achado:
                competencias.add(achado.group(1))
    return sorted(competencias)


def descobrir_competencia(share_url=SHARE_URL, log=print):
    """Descobre a competencia mais recente publicada pela Receita."""
    try:
        requisicao = urllib.request.Request(
            share_url,
            method="PROPFIND",
            headers={"Depth": "1", "User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(requisicao, timeout=60) as resposta:
            competencias = _competencias_de_xml(resposta.read())
        if competencias:
            log(f"competencia: {competencias[-1]}")
            return competencias[-1]
    except Exception as falha:  # noqa: BLE001 - fallback local
        log(f"aviso: nao descobri a competencia ({falha})")
    log(f"usando competencia padrao: {COMPETENCIA_PADRAO}")
    return COMPETENCIA_PADRAO


def baixar_arquivo(
    nome, cache_dir, log=print, tentativas=3, url_base=URL_BASE
):
    """Baixa um arquivo da Receita com cache e retry."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    destino = cache_dir / nome
    if destino.exists() and destino.stat().st_size > 0:
        log(f"cache: {nome}")
        return destino

    url = url_base.rstrip("/") + "/" + nome
    temporario = destino.with_suffix(destino.suffix + ".part")
    erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            log(f"baixando {nome} (tentativa {tentativa})")
            requisicao = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(
                requisicao, timeout=180
            ) as resposta, temporario.open("wb") as arquivo:
                esperado = resposta.headers.get("Content-Length")
                shutil.copyfileobj(resposta, arquivo, length=1024 * 1024)
            tamanho = temporario.stat().st_size
            if tamanho == 0:
                raise IOError("download vazio")
            if esperado is not None and int(esperado) != tamanho:
                raise IOError(
                    f"download incompleto: {tamanho}/{esperado} bytes"
                )
            temporario.replace(destino)
            log(f"ok: {nome} ({tamanho} bytes)")
            return destino
        except Exception as falha:  # noqa: BLE001 - retry de rede
            erro = falha
            temporario.unlink(missing_ok=True)
            if tentativa < tentativas:
                time.sleep(5 * tentativa)
    raise RuntimeError(f"falha ao baixar {nome}: {erro}")


def _ler_csv_zip(caminho):
    """Le o primeiro arquivo de dados de um zip da Receita (Latin-1, ';')."""
    with zipfile.ZipFile(caminho) as arquivo:
        nomes = [
            nome
            for nome in arquivo.namelist()
            if not nome.endswith("/")
        ]
        if not nomes:
            raise ValueError(f"nenhum arquivo em {caminho}")
        with arquivo.open(nomes[0]) as bruto:
            texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
            yield from csv.reader(texto, delimiter=";", quotechar='"')


def ler_municipio(caminho_zip, municipio):
    """Devolve o codigo de municipio usado pela Receita."""
    alvo = _chave_texto(municipio)
    for linha in _ler_csv_zip(caminho_zip):
        if len(linha) < 2:
            continue
        codigo = linha[0].strip()
        if codigo.isdigit() and _chave_texto(linha[1]) == alvo:
            return codigo
    raise ValueError(f"municipio nao encontrado: {municipio}")


def ler_cnae(caminho_zip, cnae):
    """Valida o CNAE e devolve a descricao."""
    alvo = cnae.strip()
    for linha in _ler_csv_zip(caminho_zip):
        if len(linha) >= 2 and linha[0].strip() == alvo:
            return linha[1].strip()
    raise ValueError(f"CNAE nao encontrado: {cnae}")


def _formatar_cnpj(base, ordem, dv):
    numero = f"{base}{ordem}{dv}"
    if len(numero) != 14 or not numero.isdigit():
        return numero
    return f"{numero[:2]}.{numero[2:5]}.{numero[5:8]}/{numero[8:12]}-{numero[12:]}"


def _limitar(valor, tamanho):
    return normalizar_espacos(valor)[:tamanho]


def processar_parte(
    empresas_zip,
    estabelecimentos_zip,
    codigo_municipio,
    uf,
    cnae,
    cidade=CIDADE_PADRAO,
):
    """Filtra uma parte da base e devolve linhas no schema do CSV."""
    uf = uf.strip().upper()
    cnae = cnae.strip()
    codigo_municipio = codigo_municipio.strip()

    selecionados = []
    for linha in _ler_csv_zip(estabelecimentos_zip):
        if len(linha) < 21:
            continue
        if linha[5].strip() != SITUACAO_ATIVA:
            continue
        if linha[19].strip().upper() != uf:
            continue
        if linha[20].strip() != codigo_municipio:
            continue
        if linha[11].strip() != cnae:
            continue
        selecionados.append(linha)

    if not selecionados:
        return []

    bases = {linha[0].strip() for linha in selecionados}
    razoes = {}
    for linha in _ler_csv_zip(empresas_zip):
        if len(linha) >= 2 and linha[0].strip() in bases:
            razoes[linha[0].strip()] = linha[1].strip()

    condominios = []
    for linha in selecionados:
        base = linha[0].strip()
        razao = razoes.get(base, "")
        fantasia = linha[4].strip()
        nome = nome_para_exibicao(fantasia, razao) or fantasia or razao
        if not nome:
            continue

        tipo = linha[13].strip()
        logradouro = linha[14].strip()
        endereco = capitalizar_texto(
            normalizar_espacos(f"{tipo} {logradouro}")
        )
        complemento = normalizar_espacos(linha[16])
        condominios.append(
            {
                "nome": _limitar(nome, 120),
                "endereco": _limitar(endereco, 150),
                "numero": _limitar(linha[15], 20),
                "bairro": _limitar(capitalizar_texto(linha[17]), 80),
                "cidade": _limitar(cidade, 80),
                "cep": formatar_cep(linha[18])[:9],
                "referencia": _limitar(
                    capitalizar_texto(complemento), 150
                ),
                "ativo": "sim",
                "revisado": "nao",
                "fonte": "cnpj",
                "nome_origem": _limitar(razao or fantasia, 120),
                "cnpj": _formatar_cnpj(
                    base, linha[1].strip(), linha[2].strip()
                ),
            }
        )

    return condominios


def coletar_cnpj(
    cache_dir,
    saida_csv=None,
    uf=UF_PADRAO,
    municipio=MUNICIPIO_PADRAO,
    cnae=CNAE_PADRAO,
    partes=range(10),
    cidade=CIDADE_PADRAO,
    competencia=None,
    url_base=None,
    log=print,
):
    """Baixa, filtra e devolve os condominios de uma cidade."""
    if url_base is None:
        competencia = competencia or descobrir_competencia(log=log)
        url_base = f"{SHARE_URL}{competencia}/"
    log(f"fonte cnpj: {url_base}")

    cache_dir = Path(cache_dir)
    municipios = baixar_arquivo(
        "Municipios.zip", cache_dir, log, url_base=url_base
    )
    cnaes = baixar_arquivo("Cnaes.zip", cache_dir, log, url_base=url_base)
    codigo = ler_municipio(municipios, municipio)
    log(f"municipio {municipio}: {codigo}")
    log(f"cnae {cnae}: {ler_cnae(cnaes, cnae)}")

    linhas = []
    for parte in partes:
        empresas = baixar_arquivo(
            f"Empresas{parte}.zip",
            cache_dir,
            log,
            url_base=url_base,
        )
        estabelecimentos = baixar_arquivo(
            f"Estabelecimentos{parte}.zip",
            cache_dir,
            log,
            url_base=url_base,
        )
        novas = processar_parte(
            empresas,
            estabelecimentos,
            codigo,
            uf,
            cnae,
            cidade=cidade,
        )
        linhas.extend(novas)
        log(f"parte {parte}: {len(novas)} condominio(s)")

    if saida_csv is not None:
        escrever_csv(linhas, saida_csv)
        log(f"csv: {saida_csv} ({len(linhas)} linhas)")
    return linhas
