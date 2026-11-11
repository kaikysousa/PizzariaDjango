"""Regras de entrada e transição de pedidos."""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Categoria, ItemPedido, Pedido, Produto
from .signals import pedido_itens_alterados, pedido_status_alterado

CENTAVO = Decimal("0.01")
CATEGORIAS_MEIA = {Categoria.PIZZA, Categoria.PIZZA_DOCE}
QUANTIDADE_MAXIMA = 99

STATUS_TRANSITIONS = {
    Pedido.Status.AGUARDANDO_APROVACAO: frozenset(
        {Pedido.Status.APROVADO, Pedido.Status.CANCELADO}
    ),
    Pedido.Status.APROVADO: frozenset(
        {Pedido.Status.PREPARANDO, Pedido.Status.CANCELADO}
    ),
    Pedido.Status.PREPARANDO: frozenset(
        {Pedido.Status.SAIU, Pedido.Status.CANCELADO}
    ),
    Pedido.Status.SAIU: frozenset({Pedido.Status.ENTREGUE}),
    Pedido.Status.ENTREGUE: frozenset(),
    Pedido.Status.CANCELADO: frozenset(),
}

STATUS_INICIAIS = frozenset(
    {Pedido.Status.AGUARDANDO_APROVACAO, Pedido.Status.APROVADO}
)


def _preco_unitario(produto, segundo_produto=None):
    if segundo_produto is not None:
        return ((produto.preco + segundo_produto.preco) / 2).quantize(
            CENTAVO, rounding=ROUND_HALF_UP
        )
    return produto.preco


def resolver_itens(itens, ids_permitidos=None):
    """Valida IDs e quantidades contra o banco e recalcula todo preço."""
    permitidos = set(ids_permitidos or [])
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
        if quantidade > QUANTIDADE_MAXIMA:
            raise ValidationError(
                f"A quantidade máxima por item é {QUANTIDADE_MAXIMA}."
            )
        if len(ids) not in (1, 2) or len(ids) != len(set(ids)):
            raise ValidationError("Item de pedido inválido.")

        produtos = list(
            Produto.objects.filter(
                Q(id__in=ids)
                & (Q(disponivel=True) | Q(id__in=permitidos))
            )
        )
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


def _status_inicial(origem, status_inicial, usuario=None):
    if origem not in Pedido.Origem.values:
        raise ValidationError("Origem de pedido inválida.")

    if status_inicial is None:
        status = (
            Pedido.Status.APROVADO
            if origem == Pedido.Origem.BALCAO
            else Pedido.Status.AGUARDANDO_APROVACAO
        )
    else:
        if status_inicial not in STATUS_INICIAIS:
            raise ValidationError("Status inicial inválido.")
        status = status_inicial

    if status == Pedido.Status.APROVADO:
        if origem != Pedido.Origem.BALCAO:
            raise ValidationError("Pedido aprovado só pode ser criado como balcão.")
        if usuario is None or not getattr(usuario, "is_staff", False):
            raise ValidationError("Aprovação inicial exige usuário da loja.")

    return status


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
    origem=Pedido.Origem.CLIENTE,
    condominio=None,
    status_inicial=None,
    usuario=None,
):
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    endereco = (endereco or "").strip()
    if not nome or not telefone or not endereco:
        raise ValidationError("Nome, telefone e endereço são obrigatórios.")

    status_inicial = _status_inicial(origem, status_inicial, usuario)
    resolved, total = resolver_itens(itens)
    pedido = Pedido.objects.create(
        nome=nome,
        telefone=telefone,
        endereco=endereco,
        endereco2=(endereco2 or "").strip(),
        observacoes=(observacoes or "").strip(),
        pagamento=pagamento,
        origem=origem,
        condominio=condominio,
        status=status_inicial,
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

    if status_inicial == Pedido.Status.APROVADO:
        pedido.aprovado_por = usuario
        pedido.aprovado_em = timezone.now()
        pedido.save(update_fields=["aprovado_por", "aprovado_em"])

        # Import tardio evita ciclo entre pedidos e estoque na inicialização dos apps.
        from estoque.services import consumir_pedido

        pedido.avisos_estoque = consumir_pedido(pedido, usuario=usuario)

    return pedido


@transaction.atomic
def alterar_status(pedido, novo_status, usuario=None, motivo=""):
    """Valida e aplica uma transição de status, emitindo o signal de domínio."""
    if novo_status not in Pedido.Status.values:
        raise ValidationError("Status inválido.")

    pedido_travado = Pedido.objects.select_for_update().get(pk=pedido.pk)
    status_anterior = pedido_travado.status
    permitidos = STATUS_TRANSITIONS.get(status_anterior, frozenset())
    if novo_status not in permitidos:
        raise ValidationError(
            f"Transição inválida: {status_anterior} -> {novo_status}."
        )

    campos = ["status", "atualizado_em"]
    pedido_travado.status = novo_status

    if novo_status == Pedido.Status.APROVADO:
        pedido_travado.aprovado_por = usuario
        pedido_travado.aprovado_em = timezone.now()
        campos.extend(["aprovado_por", "aprovado_em"])
    elif novo_status == Pedido.Status.CANCELADO:
        pedido_travado.motivo_cancelamento = (motivo or "").strip()
        campos.append("motivo_cancelamento")

    pedido_travado.save(update_fields=campos)
    pedido_status_alterado.send(
        sender=Pedido,
        instance=pedido_travado,
        status_anterior=status_anterior,
        status_novo=novo_status,
        usuario=usuario,
    )
    return pedido_travado


@transaction.atomic
def atualizar_itens_pedido(pedido, itens, usuario=None):
    """Substitui os itens somente enquanto o pedido permite edição."""
    pedido_travado = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if not pedido_travado.itens_editaveis:
        raise ValidationError(
            "Os itens deste pedido não podem mais ser editados."
        )

    ids_atuais = set(
        pedido_travado.itens.values_list("produto_id", flat=True)
    ) | set(
        pedido_travado.itens.exclude(segundo_produto_id=None).values_list(
            "segundo_produto_id", flat=True
        )
    )
    resolved, total = resolver_itens(itens, ids_permitidos=ids_atuais)
    pedido_travado.itens.all().delete()
    ItemPedido.objects.bulk_create(
        [
            ItemPedido(
                pedido=pedido_travado,
                produto=item["produto"],
                segundo_produto=item["segundo_produto"],
                quantidade=item["quantidade"],
                preco_unitario=item["preco_unitario"],
            )
            for item in resolved
        ]
    )
    pedido_travado.total = total
    pedido_travado.save(update_fields=["total", "atualizado_em"])
    pedido_itens_alterados.send(
        sender=Pedido,
        instance=pedido_travado,
        usuario=usuario,
    )
    return pedido_travado
