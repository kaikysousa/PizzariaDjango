"""Mescla fontes e prepara o CSV de revisao."""

from .coleta import chave_dedup, normalizar_espacos

_PRIORIDADE = {
    "manual": 0,
    "prefeitura": 1,
    "cnpj": 2,
    "cnpj+osm": 2,
    "osm": 3,
}
_OBRIGATORIOS = ("nome", "endereco", "bairro", "cidade")


def _prioridade(linha):
    fonte = normalizar_espacos(linha.get("fonte", "")).lower()
    return _PRIORIDADE.get(fonte, 99)


def mesclar(linhas):
    """Remove duplicados mantendo a fonte de maior confianca."""
    escolhidas = {}
    for linha in linhas:
        chave = chave_dedup(
            linha.get("nome", ""),
            linha.get("endereco", ""),
            linha.get("numero", ""),
            linha.get("bairro", ""),
        )
        atual = escolhidas.get(chave)
        if atual is None or _prioridade(linha) < _prioridade(atual):
            escolhidas[chave] = linha
    return sorted(
        escolhidas.values(),
        key=lambda linha: (
            normalizar_espacos(linha.get("bairro", "")).lower(),
            normalizar_espacos(linha.get("nome", "")).lower(),
        ),
    )


def separar_pendencias(linhas):
    """Separa linhas completas das que precisam de preenchimento manual."""
    validas = []
    pendencias = []
    for linha in linhas:
        if all(normalizar_espacos(linha.get(campo, "")) for campo in _OBRIGATORIOS):
            validas.append(linha)
        else:
            pendencias.append(linha)
    return validas, pendencias
