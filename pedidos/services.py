"""Regras de entrada de pedido: validação, preço e persistência."""

from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Categoria, ItemPedido, Pedido, Produto

CENTAVO = Decimal("0.01")
CATEGORIAS_MEIA = {Categoria.PIZZA, Categoria.PIZZA_DOCE}


def _preco_unitario(produto, segundo_produto=None):
    if segundo_produto is not None:
        return ((produto.preco + segundo_produto.preco) / 2).quantize(
            CENTAVO, rounding=ROUND_HALF_UP
        )
    return produto.preco


def resolver_itens(itens):
    """Valida IDs e quantidades contra o banco e recalcula todo preço."""
    if not isinstance(itens, list) or not itens:
        raise ValidationError("O carrinho está vazio.")

    resolved = []
    for bruto in itens:
        if not isinstance(bruto, dict):
            raise ValidationError("Item de pedido inválido.")

        try:
            ids = [int(valor) for valor in bruto.get("ids", [])]
            quantidade = int(bruto.get("quantidade", 0))
        except (TypeError, ValueError):
            raise ValidationError("Item de pedido inválido.")

        if quantidade < 1:
            raise ValidationError("A quantidade deve ser maior que zero.")
        if len(ids) not in (1, 2) or len(ids) != len(set(ids)):
            raise ValidationError("Item de pedido inválido.")

        produtos = list(Produto.objects.filter(id__in=ids, disponivel=True))
        if len(produtos) != len(ids):
            raise ValidationError("Produto inexistente ou indisponível.")

        por_id = {produto.id: produto for produto in produtos}
        produto = por_id[ids[0]]
        segundo = por_id[ids[1]] if len(ids) == 2 else None

        if segundo is not None and (
            produto.categoria not in CATEGORIAS_MEIA
            or segundo.categoria not in CATEGORIAS_MEIA
        ):
            raise ValidationError("Meia pizza só pode ser montada com pizzas.")

        preco = _preco_unitario(produto, segundo)
        resolved.append(
            {
                "produto": produto,
                "segundo_produto": segundo,
                "quantidade": quantidade,
                "preco_unitario": preco,
                "subtotal": preco * quantidade,
            }
        )

    total = sum((item["subtotal"] for item in resolved), start=Decimal("0.00"))
    return resolved, total


@transaction.atomic
def criar_pedido(
    *,
    itens,
    nome,
    telefone,
    endereco,
    endereco2="",
    observacoes="",
    pagamento=Pedido.Pagamento.DINHEIRO,
):
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    endereco = (endereco or "").strip()
    if not nome or not telefone or not endereco:
        raise ValidationError("Nome, telefone e endereço são obrigatórios.")

    resolved, total = resolver_itens(itens)
    pedido = Pedido.objects.create(
        nome=nome,
        telefone=telefone,
        endereco=endereco,
        endereco2=(endereco2 or "").strip(),
        observacoes=(observacoes or "").strip(),
        pagamento=pagamento,
        total=total,
    )
    ItemPedido.objects.bulk_create(
        [
            ItemPedido(
                pedido=pedido,
                produto=item["produto"],
                segundo_produto=item["segundo_produto"],
                quantidade=item["quantidade"],
                preco_unitario=item["preco_unitario"],
            )
            for item in resolved
        ]
    )
    return pedido
