from django import forms

from .models import Pedido


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            "nome",
            "telefone",
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
            "endereco": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "endereco2": forms.TextInput(attrs={"autocomplete": "address-line2"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_telefone(self):
        telefone = "".join(
            caractere for caractere in self.cleaned_data["telefone"] if caractere.isdigit()
        )
        if len(telefone) < 10:
            raise forms.ValidationError("Informe um telefone com DDD.")
        return telefone
