"""Painel operacional do dono/loja."""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from estoque.models import Ingrediente
from pedidos.models import Pedido
from pedidos.services import (
    STATUS_TRANSITIONS,
    alterar_status,
    atualizar_itens_pedido,
    criar_pedido,
)

from .forms import (
    ItemPedidoForm,
    PedidoBalcaoForm,
    assinatura_itens,
    assinatura_pedido,
    itens_do_formset,
    itens_iniciais,
)

ItemFormSet = formset_factory(
    ItemPedidoForm, extra=4, max_num=200, validate_max=True
)

ACOES_STATUS = {
    "aprovar": Pedido.Status.APROVADO,
    "preparar": Pedido.Status.PREPARANDO,
    "sair": Pedido.Status.SAIU,
    "entregar": Pedido.Status.ENTREGUE,
    "recusar": Pedido.Status.CANCELADO,
    "cancelar": Pedido.Status.CANCELADO,
}
ACOES_COM_MOTIVO = {"recusar", "cancelar"}
ROTULOS_ACAO = {
    "aprovar": "Aprovar pedido",
    "preparar": "Iniciar preparo",
    "sair": "Sair para entrega",
    "entregar": "Entregar",
    "recusar": "Recusar pedido",
    "cancelar": "Cancelar pedido",
}
ACOES_POR_DESTINO = {
    Pedido.Status.APROVADO: "aprovar",
    Pedido.Status.PREPARANDO: "preparar",
    Pedido.Status.SAIU: "sair",
    Pedido.Status.ENTREGUE: "entregar",
}
ORDEM_TRANSICOES = [
    Pedido.Status.APROVADO,
    Pedido.Status.PREPARANDO,
    Pedido.Status.SAIU,
    Pedido.Status.ENTREGUE,
    Pedido.Status.CANCELADO,
]
FLUXO_STATUS = [
    Pedido.Status.AGUARDANDO_APROVACAO,
    Pedido.Status.APROVADO,
    Pedido.Status.PREPARANDO,
    Pedido.Status.SAIU,
    Pedido.Status.ENTREGUE,
]


def _acoes_disponiveis(pedido):
    """Somente transições válidas aparecem no detalhe."""
    permitidos = STATUS_TRANSITIONS.get(pedido.status, frozenset())
    acoes = []
    for destino in ORDEM_TRANSICOES:
        if destino not in permitidos:
            continue
        if destino == Pedido.Status.CANCELADO:
            recusa = pedido.status == Pedido.Status.AGUARDANDO_APROVACAO
            acao = "recusar" if recusa else "cancelar"
            acoes.append(
                {
                    "acao": acao,
                    "rotulo": ROTULOS_ACAO[acao],
                    "motivo": True,
                    "perigo": True,
                }
            )
            continue
        acao = ACOES_POR_DESTINO[destino]
        acoes.append(
            {
                "acao": acao,
                "rotulo": ROTULOS_ACAO[acao],
                "motivo": False,
                "perigo": False,
            }
        )
    return acoes


def _avisar_estoque(request, pedido):
    for aviso in getattr(pedido, "avisos_estoque", []):
        messages.warning(request, aviso)


def _eventos_status(pedido):
    """Linha do tempo derivada dos carimbos de data disponíveis."""
    eventos = [
        {
            "rotulo": "Pedido criado",
            "quando": pedido.criado_em,
            "detalhe": f"Origem: {pedido.get_origem_display()}",
        }
    ]
    if pedido.aprovado_em is not None:
        eventos.append(
            {
                "rotulo": "Pedido aprovado",
                "quando": pedido.aprovado_em,
                "detalhe": (
                    f"Por {pedido.aprovado_por}" if pedido.aprovado_por_id else ""
                ),
            }
        )

    if pedido.status == Pedido.Status.CANCELADO:
        eventos.append(
            {
                "rotulo": "Pedido cancelado",
                "quando": pedido.atualizado_em,
                "detalhe": pedido.motivo_cancelamento,
                "perigo": True,
            }
        )
    elif pedido.status not in {
        Pedido.Status.AGUARDANDO_APROVACAO,
        Pedido.Status.APROVADO,
    }:
        eventos.append(
            {
                "rotulo": pedido.get_status_display(),
                "quando": pedido.atualizado_em,
                "detalhe": "",
            }
        )
    return eventos


def _progresso_status(pedido):
    """Etapas do fluxo, marcando o que já passou e a etapa atual."""
    if pedido.status == Pedido.Status.CANCELADO:
        return []
    atual = FLUXO_STATUS.index(pedido.status)
    progresso = []
    for indice, valor in enumerate(FLUXO_STATUS):
        if indice < atual:
            estado = "concluido"
        elif indice == atual:
            estado = "atual"
        else:
            estado = "futuro"
        progresso.append(
            {
                "valor": valor,
                "rotulo": Pedido.Status(valor).label,
                "estado": estado,
            }
        )
    return progresso


@staff_member_required
def dashboard(request):
    contagens = {
        linha["status"]: linha["total"]
        for linha in Pedido.objects.values("status").annotate(total=Count("id"))
    }
    cartoes_status = [
        {
            "status": valor,
            "rotulo": rotulo,
            "total": contagens.get(valor, 0),
        }
        for valor, rotulo in Pedido.Status.choices
    ]

    pendentes = list(
        Pedido.objects.filter(status=Pedido.Status.AGUARDANDO_APROVACAO)
        .select_related("condominio")
        .order_by("-criado_em")[:10]
    )
    em_andamento = list(
        Pedido.objects.filter(
            status__in=[Pedido.Status.PREPARANDO, Pedido.Status.SAIU]
        )
        .select_related("condominio")
        .order_by("criado_em")[:10]
    )
    ingredientes_baixos = list(
        Ingrediente.objects.filter(
            ativo=True, estoque_atual__lt=F("estoque_minimo")
        ).order_by("nome")[:20]
    )

    return render(
        request,
        "painel/dashboard.html",
        {
            "cartoes_status": cartoes_status,
            "pendentes": pendentes,
            "em_andamento": em_andamento,
            "ingredientes_baixos": ingredientes_baixos,
            "total_pendentes": contagens.get(
                Pedido.Status.AGUARDANDO_APROVACAO, 0
            ),
        },
    )


@staff_member_required
def lista_pedidos(request):
    status = (request.GET.get("status") or "").strip()
    if status not in Pedido.Status.values:
        status = ""
    busca = (request.GET.get("q") or "").strip()

    lista = Pedido.objects.select_related("condominio").order_by("-criado_em")
    if status:
        lista = lista.filter(status=status)
    if busca:
        lista = lista.filter(
            Q(nome__icontains=busca) | Q(telefone__icontains=busca)
        )

    paginador = Paginator(lista, 20)
    pagina = paginador.get_page(request.GET.get("page"))

    return render(
        request,
        "painel/pedidos/lista.html",
        {
            "page_obj": pagina,
            "status_filtro": status,
            "busca": busca,
            "statuses": Pedido.Status.choices,
        },
    )


@staff_member_required
def pedido_detalhe(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related(
            "condominio", "aprovado_por"
        ).prefetch_related("itens__produto", "itens__segundo_produto"),
        pk=pk,
    )
    return render(
        request,
        "painel/pedidos/detalhe.html",
        {
            "pedido": pedido,
            "acoes": _acoes_disponiveis(pedido),
            "eventos": _eventos_status(pedido),
            "progresso": _progresso_status(pedido),
        },
    )


@staff_member_required
def pedido_novo(request):
    if request.method == "POST":
        form = PedidoBalcaoForm(request.POST)
        formset = ItemFormSet(request.POST, prefix="itens")
        if form.is_valid() and formset.is_valid():
            itens = itens_do_formset(formset)
            if not itens:
                form.add_error(None, "Adicione pelo menos um item ao pedido.")
            else:
                try:
                    pedido = criar_pedido(
                        itens=itens,
                        origem=Pedido.Origem.BALCAO,
                        usuario=request.user,
                        **form.cleaned_data,
                    )
                except ValidationError as erro:
                    form.add_error(None, erro)
                else:
                    _avisar_estoque(request, pedido)
                    messages.success(
                        request, f"Pedido #{pedido.pk} criado no balcão."
                    )
                    return redirect("painel_pedido_detalhe", pk=pedido.pk)
        form.marcar_erros_acessiveis()
    else:
        form = PedidoBalcaoForm()
        formset = ItemFormSet(prefix="itens")

    return render(
        request,
        "painel/pedidos/form.html",
        {"form": form, "formset": formset, "pedido": None, "itens": []},
    )


@staff_member_required
def pedido_editar(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related("condominio").prefetch_related(
            "itens__produto", "itens__segundo_produto"
        ),
        pk=pk,
    )
    editavel = pedido.itens_editaveis
    produtos_extras = set()
    if editavel:
        for item in pedido.itens.all():
            produtos_extras.add(item.produto_id)
            if item.segundo_produto_id:
                produtos_extras.add(item.segundo_produto_id)

    if request.method == "POST":
        form = PedidoBalcaoForm(request.POST, instance=pedido)
        formset = (
            ItemFormSet(
                request.POST,
                prefix="itens",
                form_kwargs={"produtos_extras": produtos_extras},
            )
            if editavel
            else None
        )
        itens_validos = formset.is_valid() if formset is not None else True
        if form.is_valid() and itens_validos:
            itens = itens_do_formset(formset) if formset is not None else []
            if editavel and not itens:
                form.add_error(None, "Adicione pelo menos um item ao pedido.")
            else:
                try:
                    with transaction.atomic():
                        pedido = form.save()
                        if editavel and assinatura_itens(itens) != assinatura_pedido(
                            pedido
                        ):
                            pedido = atualizar_itens_pedido(
                                pedido, itens, usuario=request.user
                            )
                except ValidationError as erro:
                    form.add_error(None, erro)
                else:
                    _avisar_estoque(request, pedido)
                    messages.success(request, f"Pedido #{pedido.pk} atualizado.")
                    return redirect("painel_pedido_detalhe", pk=pedido.pk)
        form.marcar_erros_acessiveis()
    else:
        form = PedidoBalcaoForm(instance=pedido)
        formset = (
            ItemFormSet(
                initial=itens_iniciais(pedido),
                prefix="itens",
                form_kwargs={"produtos_extras": produtos_extras},
            )
            if editavel
            else None
        )

    return render(
        request,
        "painel/pedidos/form.html",
        {
            "form": form,
            "formset": formset,
            "pedido": pedido,
            "itens": list(pedido.itens.all()),
            "itens_editaveis": editavel,
        },
    )


@staff_member_required
@require_POST
def pedido_acao(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    acao = (request.POST.get("acao") or "").strip()
    novo_status = ACOES_STATUS.get(acao)
    if novo_status is None:
        messages.error(request, "Ação inválida.")
        return redirect("painel_pedido_detalhe", pk=pedido.pk)

    if acao == "recusar" and pedido.status != Pedido.Status.AGUARDANDO_APROVACAO:
        messages.error(request, "Só é possível recusar pedidos aguardando aprovação.")
        return redirect("painel_pedido_detalhe", pk=pedido.pk)

    motivo = (request.POST.get("motivo") or "").strip()
    if acao in ACOES_COM_MOTIVO and not motivo:
        messages.error(request, "Informe o motivo para recusar ou cancelar.")
        return redirect("painel_pedido_detalhe", pk=pedido.pk)

    try:
        pedido = alterar_status(
            pedido, novo_status, usuario=request.user, motivo=motivo
        )
    except ValidationError as erro:
        for mensagem in erro.messages:
            messages.error(request, mensagem)
    else:
        _avisar_estoque(request, pedido)
        messages.success(
            request,
            f"Pedido #{pedido.pk} agora está em “{pedido.get_status_display()}”.",
        )
    return redirect("painel_pedido_detalhe", pk=pedido.pk)


@staff_member_required
@require_POST
def sair(request):
    logout(request)
    return redirect("index")
