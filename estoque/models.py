from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Ingrediente(models.Model):
    class Unidade(models.TextChoices):
        GRAMA = "g", "Grama"
        MILILITRO = "ml", "Mililitro"
        UNIDADE = "un", "Unidade"

    nome = models.CharField(max_length=100)
    unidade = models.CharField(max_length=2, choices=Unidade.choices)
    estoque_atual = models.DecimalField(
        max_digits=10, decimal_places=3, default=0
    )
    estoque_minimo = models.DecimalField(
        max_digits=10, decimal_places=3, default=0
    )
    custo_unitario = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def abaixo_minimo(self):
        return self.estoque_atual < self.estoque_minimo


class FichaTecnica(models.Model):
    produto = models.ForeignKey(
        "pedidos.Produto",
        related_name="ficha_tecnica",
        on_delete=models.CASCADE,
    )
    ingrediente = models.ForeignKey(
        Ingrediente, related_name="fichas", on_delete=models.PROTECT
    )
    quantidade = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    class Meta:
        unique_together = [("produto", "ingrediente")]
        ordering = ["produto__nome", "ingrediente__nome"]

    def __str__(self):
        return f"{self.produto} — {self.ingrediente} ({self.quantidade})"


class MovimentoEstoque(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"
        AJUSTE = "ajuste", "Ajuste"
        PERDA = "perda", "Perda"
        ESTORNO = "estorno", "Estorno"

    ingrediente = models.ForeignKey(
        Ingrediente, related_name="movimentos", on_delete=models.PROTECT
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)
    saldo_apos = models.DecimalField(max_digits=10, decimal_places=3)
    pedido = models.ForeignKey(
        "pedidos.Pedido",
        related_name="movimentos_estoque",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    motivo = models.CharField(max_length=200, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="movimentos_estoque",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.quantidade} {self.ingrediente}"
