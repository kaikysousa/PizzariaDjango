"""Normalizacao e schema do CSV de coleta de condominios."""

import csv
import re
import unicodedata
from pathlib import Path

COLUNAS_CSV = (
    "nome",
    "endereco",
    "numero",
    "bairro",
    "cidade",
    "cep",
    "referencia",
    "ativo",
    "revisado",
    "fonte",
    "nome_origem",
    "cnpj",
)

_PREFIXOS = (
    "CONDOMINIO RESIDENCIAL",
    "CONDOMINIO DO",
    "CONDOMINIO",
    "RESIDENCIAL",
    "COND.",
    "COND",
)
_PREFIXO_EDIFICIO = "EDIFICIO"

_SUFIXO_BLOCO = re.compile(
    r"\s*(?:[-–—]\s*)?(?:BLOCO|TORRE|ENTRADA|QUADRA)\s*[A-Z0-9]+\s*$",
    re.IGNORECASE,
)
_ROMANOS = {
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
}
_CONECTIVOS = {"de", "da", "do", "das", "dos", "e"}
_VALORES_REVISADOS = {"sim", "1", "true", "yes", "s"}


def normalizar_espacos(valor):
    """Remove espacos nas pontas e colapsa espacos internos."""
    return re.sub(r"\s+", " ", (valor or "")).strip()


def sem_acento(valor):
    """Remove acentos preservando as letras."""
    decomposto = unicodedata.normalize("NFKD", valor or "")
    return "".join(
        caractere
        for caractere in decomposto
        if not unicodedata.combining(caractere)
    )


def _slug(valor):
    texto = sem_acento(normalizar_espacos(valor)).lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _remover_prefixos(nome, incluir_edificio=False):
    texto = normalizar_espacos(nome)
    prefixos = _PREFIXOS + ((_PREFIXO_EDIFICIO,) if incluir_edificio else ())
    mudou = True
    while mudou and texto:
        mudou = False
        maiusculo = sem_acento(texto.upper())
        for prefixo in prefixos:
            if maiusculo.startswith(prefixo):
                texto = texto[len(prefixo) :].strip(" -–—,;")
                mudou = True
                break
    return texto


def limpar_sufixo_bloco(nome):
    """Remove BLOCO/TORRE/ENTRADA/QUADRA no fim do nome."""
    texto = normalizar_espacos(nome)
    while True:
        novo = _SUFIXO_BLOCO.sub("", texto).strip(" -–—,;")
        if novo == texto or not novo:
            return texto
        texto = novo


def _capitalizar(nome):
    palavras = []
    for indice, palavra in enumerate(normalizar_espacos(nome).split()):
        maiuscula = palavra.upper()
        if maiuscula in _ROMANOS:
            palavras.append(maiuscula)
        elif maiuscula == _PREFIXO_EDIFICIO:
            palavras.append("Edifício")
        elif maiuscula == "CONDOMINIO":
            palavras.append("Condomínio")
        elif indice > 0 and maiuscula.lower() in _CONECTIVOS:
            palavras.append(maiuscula.lower())
        else:
            palavras.append(palavra.capitalize())
    return " ".join(palavras)


def nome_para_exibicao(nome_fantasia, razao_social):
    """Escolhe o nome que aparece no select do checkout."""
    fantasia = normalizar_espacos(nome_fantasia)
    if fantasia and _slug(fantasia) not in {
        "condominio",
        "residencial",
        "edificio",
        "condominio residencial",
    }:
        return _capitalizar(fantasia)

    original = normalizar_espacos(razao_social)
    if not original:
        return ""

    limpo = _remover_prefixos(original)
    limpo = limpar_sufixo_bloco(limpo)
    if not limpo:
        limpo = original
    return _capitalizar(limpo)


def chave_dedup(nome, endereco, numero, bairro):
    """Chave estavel para comparar condominios entre fontes."""
    nome_limpo = _remover_prefixos(nome, incluir_edificio=True)
    nome_limpo = limpar_sufixo_bloco(nome_limpo) or nome
    partes = (nome_limpo, endereco, numero, bairro)
    return "|".join(_slug(parte) for parte in partes)


def formatar_cep(cep):
    """Formata 8 digitos como 00000-000; devolve o original se nao der."""
    digitos = re.sub(r"\D", "", cep or "")
    if len(digitos) == 8:
        return f"{digitos[:5]}-{digitos[5:]}"
    return normalizar_espacos(cep)


def valor_revisado(valor):
    return normalizar_espacos(valor).lower() in _VALORES_REVISADOS


def capitalizar_texto(valor):
    """Capitaliza um texto preservando numerais romanos e 'Edifício'."""
    return _capitalizar(valor)


def escrever_csv(linhas, caminho):
    """Grava o CSV de revisao com ';' e UTF-8 com BOM (Excel pt-BR)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=COLUNAS_CSV,
            delimiter=";",
            extrasaction="ignore",
        )
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow(
                {coluna: linha.get(coluna, "") for coluna in COLUNAS_CSV}
            )


def ler_csv(caminho):
    """Le o CSV de revisao e devolve uma lista de dicionarios."""
    with Path(caminho).open(
        "r", encoding="utf-8-sig", newline=""
    ) as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))

