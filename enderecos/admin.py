from django.contrib import admin

from .models import Condominio


@admin.register(Condominio)
class CondominioAdmin(admin.ModelAdmin):
    list_display = ("nome", "bairro", "cidade", "ativo", "atualizado_em")
    search_fields = ("nome", "endereco", "bairro", "cidade", "cep")
    list_filter = ("ativo", "cidade", "bairro")
    list_editable = ("ativo",)
    readonly_fields = ("criado_em", "atualizado_em")
