"""Movimentação de estoque e integração com o ciclo de vida do pedido."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .models import FichaTecnica, Ingrediente, MovimentoEstoque

MILESSIMO = Decimal("0.001")
MEIA_PIZZA = Decimal("0.5")
ZERO = Decimal("0.000")
TIPOS_QUE_SOMAM = {
    MovimentoEstoque.Tipo.ENTRADA,
    MovimentoEstoque.Tipo.ESTORNO,
}
TIPOS_QUE_SUBTRAEM = {
    MovimentoEstoque.Tipo.SAIDA,
    MovimentoEstoque.Tipo.PERDA,
}


def _decimal(valor):
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Quantidade inválida.")


def _quantizar(valor):
    return valor.quantize(MILESSIMO, rounding=ROUND_HALF_UP)


def _aplicar_movimento(
    ingrediente, tipo, quantidade, *, pedido=None, motivo="", usuario=None
):
    """Atualiza o saldo de um ingrediente já travado e registra o movimento."""
    if tipo in TIPOS_QUE_SOMAM or tipo == MovimentoEstoque.Tipo.AJUSTE:
        delta = quantidade
    elif tipo in TIPOS_QUE_SUBTRAEM:
        delta = -quantidade
    else:
        raise ValidationError("Tipo de movimento inválido.")

    novo_saldo = _quantizar(ingrediente.estoque_atual + delta)
    ingrediente.estoque_atual = novo_saldo
    ingrediente.save(update_fields=["estoque_atual"])
    return MovimentoEstoque.objects.create(
        ingrediente=ingrediente,
        tipo=tipo,
        quantidade=_quantizar(quantidade),
        saldo_apos=novo_saldo,
        pedido=pedido,
        motivo=(motivo or "").strip(),
        criado_por=usuario,
    )


@transaction.atomic
def registrar_movimento(
    ingrediente,
    tipo,
    quantidade,
    *,
    pedido=None,
    motivo="",
    usuario=None,
):
    """Registra entrada, saída, ajuste ou perda manual."""
    if tipo not in MovimentoEstoque.Tipo.values:
        raise ValidationError("Tipo de movimento inválido.")

    quantidade = _quantizar(_decimal(quantidade))
    if quantidade == ZERO:
        raise ValidationError("A quantidade do movimento não pode ser zero.")
    if tipo != MovimentoEstoque.Tipo.AJUSTE and quantidade < ZERO:
        raise ValidationError("A quantidade deve ser maior que zero.")

    ingrediente_id = getattr(ingrediente, "pk", ingrediente)
    travado = Ingrediente.objects.select_for_update().get(pk=ingrediente_id)
    return _aplicar_movimento(
        travado,
        tipo,
        quantidade,
        pedido=pedido,
        motivo=motivo,
        usuario=usuario,
    )


def _necessidades_do_pedido(pedido):
    """Calcula o consumo por ingrediente e os avisos de produtos sem ficha."""
    itens = list(
        pedido.itens.select_related("produto", "segundo_produto")
    )
    produtos = {}
    for item in itens:
        produtos[item.produto_id] = item.produto
        if item.segundo_produto_id:
            produtos[item.segundo_produto_id] = item.segundo_produto

    fichas = {}
    for ficha in FichaTecnica.objects.filter(
        produto_id__in=produtos
    ).select_related("ingrediente"):
        fichas.setdefault(ficha.produto_id, []).append(ficha)

    necessidades = {}
    ingredientes = {}
    avisos = []
    for item in itens:
        if item.segundo_produto_id:
            pares = (
                (item.produto, MEIA_PIZZA),
                (item.segundo_produto, MEIA_PIZZA),
            )
        else:
            pares = ((item.produto, Decimal("1")),)

        for produto, fator in pares:
            fichas_produto = fichas.get(produto.id, [])
            if not fichas_produto:
                aviso = (
                    f"Produto sem ficha técnica: {produto.nome}. "
                    "Estoque não foi baixado."
                )
                if aviso not in avisos:
                    avisos.append(aviso)
                continue

            for ficha in fichas_produto:
                consumo = item.quantidade * fator * ficha.quantidade
                ingrediente_id = ficha.ingrediente_id
                necessidades[ingrediente_id] = (
                    necessidades.get(ingrediente_id, ZERO) + consumo
                )
                ingredientes[ingrediente_id] = ficha.ingrediente

    return necessidades, ingredientes, avisos


@transaction.atomic
def consumir_pedido(pedido, usuario=None):
    """Baixa o estoque dos itens do pedido, retornando avisos."""
    necessidades, ingredientes, avisos = _necessidades_do_pedido(pedido)
    if not necessidades:
        return avisos

    travados = {
        ingrediente.pk: ingrediente
        for ingrediente in Ingrediente.objects.select_for_update()
        .filter(pk__in=necessidades)
        .order_by("pk")
    }
    for ingrediente_id in sorted(necessidades):
        quantidade = _quantizar(necessidades[ingrediente_id])
        if quantidade == ZERO:
            continue
        _aplicar_movimento(
            travados[ingrediente_id],
            MovimentoEstoque.Tipo.SAIDA,
            quantidade,
            pedido=pedido,
            motivo=f"Consumo do pedido #{pedido.pk}",
            usuario=usuario,
        )
    return avisos


def _consumo_liquido(pedido):
    """Saldo ainda consumido por pedido, descontando estornos anteriores."""
    saldos = {}
    linhas = (
        MovimentoEstoque.objects.filter(
            pedido=pedido,
            tipo__in=(
                MovimentoEstoque.Tipo.SAIDA,
                MovimentoEstoque.Tipo.ESTORNO,
            ),
        )
        .values("ingrediente_id", "tipo")
        .annotate(total=Sum("quantidade"))
    )
    for linha in linhas:
        total = linha["total"] or ZERO
        if linha["tipo"] == MovimentoEstoque.Tipo.SAIDA:
            saldos[linha["ingrediente_id"]] = (
                saldos.get(linha["ingrediente_id"], ZERO) + total
            )
        else:
            saldos[linha["ingrediente_id"]] = (
                saldos.get(linha["ingrediente_id"], ZERO) - total
            )
    return {
        ingrediente_id: quantidade
        for ingrediente_id, quantidade in saldos.items()
        if quantidade > ZERO
    }


@transaction.atomic
def estornar_pedido(pedido, usuario=None):
    """Devolve ao estoque o consumo líquido do pedido, sem duplicar estornos."""
    consumos = _consumo_liquido(pedido)
    if not consumos:
        return []

    travados = {
        ingrediente.pk: ingrediente
        for ingrediente in Ingrediente.objects.select_for_update()
        .filter(pk__in=consumos)
        .order_by("pk")
    }
    movimentos = []
    for ingrediente_id in sorted(consumos):
        movimentos.append(
            _aplicar_movimento(
                travados[ingrediente_id],
                MovimentoEstoque.Tipo.ESTORNO,
                consumos[ingrediente_id],
                pedido=pedido,
                motivo=f"Estorno do pedido #{pedido.pk}",
                usuario=usuario,
            )
        )
    return movimentos


@transaction.atomic
def reprocessar_pedido(pedido, usuario=None):
    """Estorna o consumo atual e reaplica com base nos itens vigentes."""
    estornar_pedido(pedido, usuario=usuario)
    return consumir_pedido(pedido, usuario=usuario)
