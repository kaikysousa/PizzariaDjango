import uuid

from django.db import models


class Categoria(models.TextChoices):
    PIZZA = "pizza", "Pizza"
    PIZZA_DOCE = "pizza doce", "Pizza doce"
    BEBIDA = "bebida", "Bebida"


class Produto(models.Model):
    nome = models.CharField(max_length=100, db_index=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(
        max_length=20, choices=Categoria.choices, db_index=True
    )
    descricao = models.TextField(blank=True, null=True)
    disponivel = models.BooleanField(default=True)

    class Meta:
        ordering = ["categoria", "nome"]
        indexes = [models.Index(fields=["categoria", "nome"])]

    def __str__(self):
        return self.nome


class Pedido(models.Model):
    class Status(models.TextChoices):
        NOVO = "novo", "Novo"
        PREPARANDO = "preparando", "Preparando"
        SAIU = "saiu", "Saiu para entrega"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    class Pagamento(models.TextChoices):
        DINHEIRO = "dinheiro", "Dinheiro"
        PIX = "pix", "Pix"
        CARTAO = "cartao", "Cartão"

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nome = models.CharField("nome", max_length=100)
    telefone = models.CharField("telefone", max_length=20)
    endereco = models.CharField("endereço", max_length=150)
    endereco2 = models.CharField("complemento", max_length=100, blank=True)
    observacoes = models.TextField("observações", blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NOVO
    )
    pagamento = models.CharField(
        max_length=20, choices=Pagamento.choices, default=Pagamento.DINHEIRO
    )
    legacy_items = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Pedido #{self.pk} — {self.nome}"

    def recalcular_total(self, salvar=True):
        total = sum((item.subtotal for item in self.itens.all()), start=0)
        self.total = total
        if salvar:
            self.save(update_fields=["total", "atualizado_em"])
        return total


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido, related_name="itens", on_delete=models.CASCADE
    )
    produto = models.ForeignKey(
        Produto, related_name="itens_pedido", on_delete=models.PROTECT
    )
    segundo_produto = models.ForeignKey(
        Produto,
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantidade}x {self.nome}"

    @property
    def nome(self):
        if self.segundo_produto_id:
            return f"{self.produto.nome} / {self.segundo_produto.nome}"
        return self.produto.nome

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade
