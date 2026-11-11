from decimal import Decimal

from django import forms

from .models import MovimentoEstoque


class AjusteEstoqueForm(forms.Form):
    """Ajuste manual de saldo limitado aos tipos operacionais."""

    TIPOS_PERMITIDOS = (
        (MovimentoEstoque.Tipo.ENTRADA, "Entrada"),
        (MovimentoEstoque.Tipo.AJUSTE, "Ajuste"),
        (MovimentoEstoque.Tipo.PERDA, "Perda"),
    )

    tipo = forms.ChoiceField(
        label="Tipo de movimento",
        choices=TIPOS_PERMITIDOS,
        widget=forms.Select(attrs={"class": "campo__controle"}),
    )
    quantidade = forms.DecimalField(
        label="Quantidade",
        max_digits=10,
        decimal_places=3,
        min_value=Decimal("0.001"),
        widget=forms.NumberInput(
            attrs={
                "class": "campo__controle",
                "step": "0.001",
                "min": "0.001",
                "inputmode": "decimal",
                "autofocus": True,
            }
        ),
    )
    motivo = forms.CharField(
        label="Motivo",
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "campo__controle",
                "maxlength": 200,
                "placeholder": "Ex.: compra do fornecedor, quebra de embalagem",
            }
        ),
    )

    def clean_motivo(self):
        motivo = (self.cleaned_data.get("motivo") or "").strip()
        if not motivo:
            raise forms.ValidationError("Informe o motivo do ajuste.")
        return motivo
