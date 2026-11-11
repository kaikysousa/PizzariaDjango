from django.contrib import admin

from .models import FichaTecnica, Ingrediente, MovimentoEstoque


@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "unidade",
        "estoque_atual",
        "estoque_minimo",
        "abaixo_minimo",
        "ativo",
    )
    search_fields = ("nome",)
    list_filter = ("unidade", "ativo")
    list_editable = ("ativo",)

    @admin.display(boolean=True, description="Abaixo do mínimo")
    def abaixo_minimo(self, obj):
        return obj.abaixo_minimo


@admin.register(FichaTecnica)
class FichaTecnicaAdmin(admin.ModelAdmin):
    list_display = ("produto", "ingrediente", "quantidade")
    search_fields = ("produto__nome", "ingrediente__nome")
    list_filter = ("ingrediente",)
    list_editable = ("quantidade",)
    list_select_related = ("produto", "ingrediente")


@admin.register(MovimentoEstoque)
class MovimentoEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "criado_em",
        "ingrediente",
        "tipo",
        "quantidade",
        "saldo_apos",
        "pedido",
        "criado_por",
    )
    search_fields = ("ingrediente__nome", "motivo")
    list_filter = ("tipo", "ingrediente", "criado_em")
    date_hierarchy = "criado_em"
    list_select_related = ("ingrediente", "pedido", "criado_por")
    readonly_fields = (
        "ingrediente",
        "tipo",
        "quantidade",
        "saldo_apos",
        "pedido",
        "motivo",
        "criado_por",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
