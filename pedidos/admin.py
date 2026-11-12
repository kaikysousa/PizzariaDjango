from django.contrib import admin

from estoque.models import FichaTecnica

from .models import ItemPedido, Pedido, Produto


class FichaTecnicaInline(admin.TabularInline):
    model = FichaTecnica
    extra = 0
    fields = ("ingrediente", "quantidade", "unidade")
    readonly_fields = ("unidade",)
    autocomplete_fields = ("ingrediente",)
    verbose_name = "Ficha técnica"
    verbose_name_plural = "Fichas técnicas"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("ingrediente")

    @admin.display(description="Unidade")
    def unidade(self, obj):
        if not obj or not obj.ingrediente_id:
            return "—"
        return obj.ingrediente.get_unidade_display()


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "disponivel")
    list_filter = ("categoria", "disponivel")
    search_fields = ("nome", "descricao")
    list_editable = ("disponivel",)
    inlines = [FichaTecnicaInline]


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    can_delete = False
    fields = (
        "produto",
        "segundo_produto",
        "quantidade",
        "preco_unitario",
        "subtotal",
    )
    readonly_fields = fields

    def subtotal(self, obj):
        return obj.subtotal

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "condominio_exibicao",
        "total",
        "status",
        "pagamento",
        "criado_em",
    )
    list_filter = ("status", "pagamento", "criado_em")
    search_fields = (
        "nome",
        "telefone",
        "endereco",
        "condominio_nome",
        "condominio__nome",
    )
    readonly_fields = (
        "token",
        "total",
        "status",
        "aprovado_por",
        "aprovado_em",
        "motivo_cancelamento",
        "legacy_items",
        "criado_em",
        "atualizado_em",
    )
    date_hierarchy = "criado_em"
    inlines = [ItemPedidoInline]

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Condomínio")
    def condominio_exibicao(self, obj):
        return obj.condominio_exibicao or "-"
