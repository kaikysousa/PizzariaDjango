from django import forms

from enderecos.models import Condominio

from .models import Pedido


class CondominioSelect(forms.Select):
    """Select de condomínio com os dados de endereço em cada opção."""

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )
        condominio = getattr(value, "instance", None)
        if condominio is not None and condominio.pk:
            option["attrs"].update(
                {
                    "data-endereco": condominio.endereco,
                    "data-numero": condominio.numero,
                    "data-bairro": condominio.bairro,
                    "data-cidade": condominio.cidade,
                    "data-cep": condominio.cep,
                }
            )
        return option


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            "nome",
            "telefone",
            "condominio",
            "endereco",
            "endereco2",
            "observacoes",
            "pagamento",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"autocomplete": "name"}),
            "telefone": forms.TextInput(
                attrs={"autocomplete": "tel", "inputmode": "tel"}
            ),
            "condominio": CondominioSelect,
            "endereco": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "endereco2": forms.TextInput(attrs={"autocomplete": "address-line2"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "condominio": "Condomínio",
        }
        help_texts = {
            "condominio": (
                "Selecione o condomínio para preencher o endereço automaticamente."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["condominio"].queryset = Condominio.objects.filter(ativo=True)
        self.fields["condominio"].required = False
        self.fields["condominio"].empty_label = "Sem condomínio"
        self.fields["endereco"].required = False
        for nome, field in self.fields.items():
            field.widget.attrs.setdefault("aria-describedby", f"erro-id_{nome}")

    def marcar_erros_acessiveis(self):
        for nome, field in self.fields.items():
            if self.errors.get(nome):
                field.widget.attrs["aria-invalid"] = "true"

    def clean_telefone(self):
        telefone = "".join(
            caractere
            for caractere in self.cleaned_data.get("telefone", "")
            if caractere.isdigit()
        )
        if len(telefone) < 10:
            raise forms.ValidationError("Informe um telefone com DDD.")
        return telefone

    def clean(self):
        cleaned_data = super().clean()
        condominio = cleaned_data.get("condominio")
        endereco = (cleaned_data.get("endereco") or "").strip()

        if not endereco and condominio is not None:
            endereco = condominio.endereco_completo

        if not endereco:
            self.add_error(
                "endereco", "Informe o endereço ou selecione um condomínio."
            )
        elif len(endereco) > 255:
            self.add_error(
                "endereco",
                "Endereço muito longo (máximo 255 caracteres). "
                "Ajuste o condomínio ou preencha manualmente.",
            )
        else:
            cleaned_data["endereco"] = endereco

        return cleaned_data
