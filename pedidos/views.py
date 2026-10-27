import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PedidoForm
from .models import Categoria, Pedido, Produto
from .services import criar_pedido, resolver_itens


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

    page_obj = Paginator(produtos, 4).get_page(request.GET.get("page"))

    return render(
        request,
        "pedidos/index.html",
        {
            "page_obj": page_obj,
            "produtos": page_obj.object_list,
            "busca": busca,
            "categoria_ativa": categoria,
            "categorias": Categoria.choices,
        },
    )


@require_POST
def revisar_pedido(request):
    try:
        payload = json.loads(request.POST.get("carrinho") or "")
        itens = payload.get("itens")
        if not isinstance(itens, list) or not itens:
            raise ValueError("carrinho vazio")
        normalizados = [
            {"ids": [int(valor) for valor in item["ids"]], "quantidade": int(item["quantidade"])}
            for item in itens
        ]
        resolver_itens(normalizados)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, ValidationError):
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
        form = PedidoForm(request.POST)
        if form.is_valid():
            try:
                pedido = criar_pedido(itens=request.session["carrinho"], **form.cleaned_data)
            except ValidationError as erro:
                form.add_error(None, erro)
            else:
                request.session.pop("carrinho", None)
                return redirect("recibo", token=pedido.token)
    else:
        form = PedidoForm()

    return render(
        request,
        "pedidos/checkout.html",
        {"itens": itens, "total": total, "form": form},
    )


def recibo(request, token):
    pedido = get_object_or_404(Pedido, token=token)
    return render(request, "pedidos/recibo.html", {"pedido": pedido})


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
