from django.contrib import admin

from .models import ItemPedido, Pedido, Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "disponivel")
    list_filter = ("categoria", "disponivel")
    search_fields = ("nome", "descricao")
    list_editable = ("disponivel",)


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
    list_display = ("id", "nome", "total", "status", "pagamento", "criado_em")
    list_filter = ("status", "pagamento", "criado_em")
    search_fields = ("nome", "telefone", "endereco")
    readonly_fields = (
        "token",
        "total",
        "legacy_items",
        "criado_em",
        "atualizado_em",
    )
    date_hierarchy = "criado_em"
    inlines = [ItemPedidoInline]
