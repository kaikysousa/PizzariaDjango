"""Painel operacional de estoque."""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db.models import F, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from pedidos.models import Produto

from .forms import AjusteEstoqueForm
from .models import Ingrediente, MovimentoEstoque
from .services import registrar_movimento

STATUS_CHOICES = (
    ("", "Todos"),
    ("abaixo", "Abaixo do mínimo"),
    ("ok", "No mínimo ou acima"),
    ("inativos", "Inativos"),
)
STATUS_VALIDOS = {valor for valor, _ in STATUS_CHOICES}
PRODUTOS_SEM_FICHA_EXIBIDOS = 12


def _formatar_quantidade(valor):
    texto = f"{valor:.3f}".rstrip("0").rstrip(".")
    return (texto or "0").replace(".", ",")


def _saldo_anterior(movimento):
    """Deriva o saldo anterior do movimento já gravado, sem leitura suja."""
    if movimento.tipo == MovimentoEstoque.Tipo.PERDA:
        return movimento.saldo_apos + movimento.quantidade
    return movimento.saldo_apos - movimento.quantidade


@staff_member_required
@require_GET
def lista(request):
    busca = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    if status not in STATUS_VALIDOS:
        status = ""

    ingredientes = Ingrediente.objects.annotate(
        ultima_movimentacao=Max("movimentos__criado_em")
    )
    if busca:
        ingredientes = ingredientes.filter(nome__icontains=busca)
    if status == "abaixo":
        ingredientes = ingredientes.filter(estoque_atual__lt=F("estoque_minimo"))
    elif status == "ok":
        ingredientes = ingredientes.filter(estoque_atual__gte=F("estoque_minimo"))
    elif status == "inativos":
        ingredientes = ingredientes.filter(ativo=False)
    ingredientes = ingredientes.order_by("nome")

    produtos_sem_ficha = Produto.objects.filter(
        disponivel=True, ficha_tecnica__isnull=True
    ).order_by("nome")
    produtos_sem_ficha_total = produtos_sem_ficha.count()

    return render(
        request,
        "estoque/lista.html",
        {
            "ingredientes": ingredientes,
            "busca": busca,
            "status_ativo": status,
            "status_choices": STATUS_CHOICES,
            "total_ingredientes": Ingrediente.objects.count(),
            "total_abaixo_minimo": Ingrediente.objects.filter(
                ativo=True, estoque_atual__lt=F("estoque_minimo")
            ).count(),
            "produtos_sem_ficha": produtos_sem_ficha[
                :PRODUTOS_SEM_FICHA_EXIBIDOS
            ],
            "produtos_sem_ficha_total": produtos_sem_ficha_total,
            "produtos_sem_ficha_restantes": max(
                produtos_sem_ficha_total - PRODUTOS_SEM_FICHA_EXIBIDOS, 0
            ),
        },
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def ajustar(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    saldo_antes = ingrediente.estoque_atual
    form = AjusteEstoqueForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            movimento = registrar_movimento(
                ingrediente,
                form.cleaned_data["tipo"],
                form.cleaned_data["quantidade"],
                motivo=form.cleaned_data["motivo"],
                usuario=request.user,
            )
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(
                request,
                (
                    "Ajuste registrado com sucesso. "
                    f"{movimento.get_tipo_display()} de "
                    f"{_formatar_quantidade(movimento.quantidade)} "
                    f"{ingrediente.unidade} em {ingrediente.nome}. "
                    f"Saldo: {_formatar_quantidade(_saldo_anterior(movimento))} "
                    f"→ {_formatar_quantidade(movimento.saldo_apos)} "
                    f"{ingrediente.unidade}."
                ),
            )
            return redirect("estoque:lista")

    movimentos = ingrediente.movimentos.select_related("criado_por")[:10]

    return render(
        request,
        "estoque/ajustar.html",
        {
            "ingrediente": ingrediente,
            "form": form,
            "saldo_antes": saldo_antes,
            "saldo_inicial_js": str(saldo_antes),
            "movimentos": movimentos,
        },
    )
