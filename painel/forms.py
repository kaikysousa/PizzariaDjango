"""Formulários do painel de pedidos."""

from django import forms

from enderecos.models import Condominio
from pedidos.models import Pedido, Produto
from pedidos.services import CATEGORIAS_MEIA


class ItemPedidoForm(forms.Form):
    """Linha do formset de itens; preços nunca vêm do navegador."""

    produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        label="Produto",
        empty_label="Selecione um produto",
    )
    segundo_produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        label="Segundo produto (meia)",
        required=False,
        empty_label="Sem segundo sabor",
    )
    quantidade = forms.IntegerField(
        label="Quantidade",
        min_value=1,
        max_value=99,
        widget=forms.NumberInput(attrs={"placeholder": "1"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        disponiveis = Produto.objects.filter(disponivel=True)
        self.fields["produto"].queryset = disponiveis
        self.fields["segundo_produto"].queryset = disponiveis

    def clean(self):
        cleaned = super().clean()
        produto = cleaned.get("produto")
        segundo = cleaned.get("segundo_produto")
        if segundo is not None and produto is not None:
            if (
                produto.categoria not in CATEGORIAS_MEIA
                or segundo.categoria not in CATEGORIAS_MEIA
            ):
                self.add_error(
                    "segundo_produto", "Meia pizza só pode ser montada com pizzas."
                )
        return cleaned


class PedidoBalcaoForm(forms.ModelForm):
    """Dados de cliente e entrega de um pedido criado no balcão."""

    class Meta:
        model = Pedido
        fields = [
            "nome",
            "telefone",
            "condominio",
            "endereco",
            "endereco2",
            "pagamento",
            "observacoes",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"autocomplete": "name"}),
            "telefone": forms.TextInput(
                attrs={"autocomplete": "tel", "inputmode": "tel"}
            ),
            "endereco": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "endereco2": forms.TextInput(attrs={"autocomplete": "address-line2"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["condominio"].queryset = Condominio.objects.filter(ativo=True)
        self.fields["condominio"].required = False
        self.fields["condominio"].empty_label = "Sem condomínio"
        self.fields["endereco"].required = False
        for nome, field in self.fields.items():
            field.widget.attrs.setdefault("aria-describedby", f"erro-{nome}")

    def marcar_erros_acessiveis(self):
        for nome, field in self.fields.items():
            if self.errors.get(nome):
                field.widget.attrs["aria-invalid"] = "true"

    def clean_telefone(self):
        telefone = "".join(
            caractere for caractere in self.cleaned_data["telefone"] if caractere.isdigit()
        )
        if len(telefone) < 10:
            raise forms.ValidationError("Informe um telefone com DDD.")
        return telefone

    def _endereco_do_condominio(self):
        condominio = self.cleaned_data.get("condominio")
        if condominio is None:
            return ""
        return condominio.endereco_completo

    def clean(self):
        cleaned = super().clean()
        condominio = cleaned.get("condominio")
        endereco = (cleaned.get("endereco") or "").strip()

        if not endereco and condominio is not None:
            endereco = self._endereco_do_condominio()

        if not endereco:
            self.add_error(
                "endereco", "Informe o endereço ou escolha um condomínio."
            )
        cleaned["endereco"] = endereco
        return cleaned


def itens_do_formset(formset):
    """Converte um formset válido no payload aceito por resolver_itens."""
    itens = []
    for form in formset:
        dados = form.cleaned_data
        produto = dados.get("produto")
        if produto is None:
            continue
        ids = [produto.id]
        segundo = dados.get("segundo_produto")
        if segundo is not None:
            ids.append(segundo.id)
        itens.append({"ids": ids, "quantidade": dados["quantidade"]})
    return itens


def itens_iniciais(pedido):
    """Dados iniciais do formset a partir dos itens salvos."""
    return [
        {
            "produto": item.produto_id,
            "segundo_produto": item.segundo_produto_id,
            "quantidade": item.quantidade,
        }
        for item in pedido.itens.all()
    ]


def assinatura_itens(itens):
    """Identidade estável de uma lista de itens para evitar reprocessamento à toa."""
    return sorted(
        (
            tuple(item["ids"]),
            item["quantidade"],
        )
        for item in itens
    )


def assinatura_pedido(pedido):
    return sorted(
        (
            tuple(
                [item.produto_id]
                + ([item.segundo_produto_id] if item.segundo_produto_id else [])
            ),
            item.quantidade,
        )
        for item in pedido.itens.all()
    )
