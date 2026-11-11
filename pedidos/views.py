import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .forms import PedidoForm
from .models import Categoria, Pedido, Produto
from .services import criar_pedido, resolver_itens

STATUS_COM_RECIBO = frozenset(
    {
        Pedido.Status.APROVADO,
        Pedido.Status.PREPARANDO,
        Pedido.Status.SAIU,
        Pedido.Status.ENTREGUE,
    }
)

ETAPAS_ACOMPANHAMENTO = [
    (Pedido.Status.AGUARDANDO_APROVACAO, "Pedido recebido"),
    (Pedido.Status.APROVADO, "Aprovado pela loja"),
    (Pedido.Status.PREPARANDO, "Em preparo"),
    (Pedido.Status.SAIU, "Saiu para entrega"),
    (Pedido.Status.ENTREGUE, "Entregue"),
]


def index(request):
    produtos = Produto.objects.filter(disponivel=True)

    busca = (request.GET.get("q") or "").strip()
    if busca:
        produtos = produtos.filter(nome__icontains=busca)

    categoria = (request.GET.get("categoria") or "").strip()
    if categoria in Categoria.values:
        produtos = produtos.filter(categoria=categoria)
    else:
        categoria = ""

    produtos = list(produtos)

    grupos = [
        {
            "valor": valor,
            "rotulo": rotulo,
            "produtos": [produto for produto in produtos if produto.categoria == valor],
        }
        for valor, rotulo in Categoria.choices
    ]
    grupos = [grupo for grupo in grupos if grupo["produtos"]]

    return render(
        request,
        "pedidos/index.html",
        {
            "grupos": grupos,
            "produtos": produtos,
            "busca": busca,
            "categoria_ativa": categoria,
            "categorias": Categoria.choices,
        },
    )


@require_POST
def revisar_pedido(request):
    try:
        payload = json.loads(request.POST.get("carrinho") or "")
        if not isinstance(payload, dict):
            raise ValueError("payload precisa ser objeto")
        itens = payload.get("itens")
        if not isinstance(itens, list) or not itens:
            raise ValueError("carrinho vazio")
        normalizados = [
            {
                "ids": [int(valor) for valor in item["ids"]],
                "quantidade": int(item["quantidade"]),
            }
            for item in itens
        ]
        resolver_itens(normalizados)
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        json.JSONDecodeError,
        ValidationError,
    ):
        messages.error(request, "Não foi possível revisar o carrinho. Tente novamente.")
        return redirect("index")

    request.session["carrinho"] = normalizados
    return redirect("checkout")


def _carrinho_da_sessao(request):
    carrinho = request.session.get("carrinho") or []
    try:
        return resolver_itens(carrinho)
    except ValidationError:
        request.session.pop("carrinho", None)
        return [], 0


def checkout(request):
    itens, total = _carrinho_da_sessao(request)
    if not itens:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("index")

    if request.method == "POST":
        token_sessao = request.session.pop("checkout_token", None)
        token_enviado = request.POST.get("checkout_token")
        if not token_sessao or token_enviado != token_sessao:
            messages.error(request, "Este pedido já foi enviado. Confira o carrinho.")
            return redirect("checkout")

        form = PedidoForm(request.POST)
        if form.is_valid():
            try:
                pedido = criar_pedido(
                    itens=request.session["carrinho"], **form.cleaned_data
                )
            except ValidationError as erro:
                form.add_error(None, erro)
            else:
                request.session.pop("carrinho", None)
                return redirect("acompanhar_pedido", token=pedido.token)

        form.marcar_erros_acessiveis()
        request.session["checkout_token"] = uuid.uuid4().hex
    else:
        form = PedidoForm()
        request.session["checkout_token"] = uuid.uuid4().hex

    return render(
        request,
        "pedidos/checkout.html",
        {
            "itens": itens,
            "total": total,
            "form": form,
            "checkout_token": request.session["checkout_token"],
        },
    )


@never_cache
def recibo(request, token):
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related(
            "itens__produto", "itens__segundo_produto"
        ),
        token=token,
    )
    response = render(
        request,
        "pedidos/recibo.html",
        {"pedido": pedido, "pizzaria_cnpj": settings.PIZZARIA_CNPJ},
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _etapas_do_pedido(pedido):
    """Monta a timeline com o estado de cada etapa do pedido."""
    ordem = [status for status, _ in ETAPAS_ACOMPANHAMENTO]
    if pedido.status not in ordem:
        return []

    indice_atual = ordem.index(pedido.status)
    etapas = []
    for indice, (status, rotulo) in enumerate(ETAPAS_ACOMPANHAMENTO):
        if indice < indice_atual:
            estado = "concluida"
        elif indice == indice_atual:
            estado = "atual"
        else:
            estado = "pendente"
        etapas.append({"status": status, "rotulo": rotulo, "estado": estado})
    return etapas


@never_cache
def acompanhar_pedido(request, token):
    pedido = get_object_or_404(
        Pedido.objects.select_related("condominio").prefetch_related(
            "itens__produto", "itens__segundo_produto"
        ),
        token=token,
    )
    response = render(
        request,
        "pedidos/acompanhar.html",
        {
            "pedido": pedido,
            "etapas": _etapas_do_pedido(pedido),
            "mostrar_recibo": pedido.status in STATUS_COM_RECIBO,
            "aguardando_aprovacao": (
                pedido.status == Pedido.Status.AGUARDANDO_APROVACAO
            ),
            "cancelado": pedido.status == Pedido.Status.CANCELADO,
        },
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def carrinho_json(request):
    """Endpoint opcional para depuração do carrinho da sessão."""
    itens, total = _carrinho_da_sessao(request)
    return JsonResponse(
        {
            "itens": [
                {
                    "nome": item["produto"].nome,
                    "quantidade": item["quantidade"],
                    "subtotal": str(item["subtotal"]),
                }
                for item in itens
            ],
            "total": str(total),
        }
    )
