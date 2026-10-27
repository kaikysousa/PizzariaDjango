from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from pedidos.models import Categoria, ItemPedido, Pedido, Produto
from pedidos.services import criar_pedido, resolver_itens


class IntakeTests(TestCase):
    def setUp(self):
        self.margherita = Produto.objects.create(
            nome="Margherita", preco="45.90", categoria=Categoria.PIZZA
        )
        self.calabresa = Produto.objects.create(
            nome="Calabresa", preco="49.90", categoria=Categoria.PIZZA
        )
        self.coca = Produto.objects.create(
            nome="Coca-Cola", preco="12.00", categoria=Categoria.BEBIDA
        )

    def test_cria_pedido_e_recalcula_total(self):
        pedido = criar_pedido(
            itens=[{"ids": [self.margherita.id], "quantidade": 2}],
            nome="Ana",
            telefone="11999999999",
            endereco="Rua A, 1",
        )
        self.assertEqual(pedido.total, Decimal("91.80"))
        self.assertEqual(pedido.itens.count(), 1)
        item = pedido.itens.get()
        self.assertEqual(item.preco_unitario, Decimal("45.90"))
        self.assertEqual(item.subtotal, Decimal("91.80"))

    def test_ignora_preco_enviado_pelo_cliente(self):
        pedido = criar_pedido(
            itens=[
                {
                    "ids": [self.margherita.id],
                    "quantidade": 1,
                    "preco": "0.01",
                    "total": "0.01",
                }
            ],
            nome="Ana",
            telefone="11999999999",
            endereco="Rua A, 1",
        )
        self.assertEqual(pedido.total, Decimal("45.90"))

    def test_rejeita_quantidade_zero(self):
        with self.assertRaises(ValidationError):
            resolver_itens([{"ids": [self.margherita.id], "quantidade": 0}])

    def test_rejeita_produto_inexistente(self):
        with self.assertRaises(ValidationError):
            resolver_itens([{"ids": [9999], "quantidade": 1}])

    def test_rejeita_produto_indisponivel(self):
        self.margherita.disponivel = False
        self.margherita.save(update_fields=["disponivel"])
        with self.assertRaises(ValidationError):
            resolver_itens([{"ids": [self.margherita.id], "quantidade": 1}])

    def test_meia_pizza_usa_media_dos_sabores(self):
        pedido = criar_pedido(
            itens=[{"ids": [self.margherita.id, self.calabresa.id], "quantidade": 1}],
            nome="Ana",
            telefone="11999999999",
            endereco="Rua A, 1",
        )
        item = pedido.itens.get()
        self.assertEqual(item.preco_unitario, Decimal("47.90"))
        self.assertEqual(item.nome, "Margherita / Calabresa")
        self.assertEqual(pedido.total, Decimal("47.90"))

    def test_rejeita_meia_com_bebida(self):
        with self.assertRaises(ValidationError):
            resolver_itens(
                [{"ids": [self.margherita.id, self.coca.id], "quantidade": 1}]
            )

    def test_rejeita_carrinho_vazio(self):
        with self.assertRaises(ValidationError):
            resolver_itens([])

    def test_rejeita_dados_do_cliente_vazios(self):
        with self.assertRaises(ValidationError):
            criar_pedido(
                itens=[{"ids": [self.margherita.id], "quantidade": 1}],
                nome="",
                telefone="",
                endereco="",
            )

    def test_recalcula_total_a_partir_dos_itens(self):
        pedido = Pedido.objects.create(
            nome="Ana",
            telefone="11999999999",
            endereco="Rua A, 1",
            total="0.01",
        )
        ItemPedido.objects.create(
            pedido=pedido,
            produto=self.margherita,
            quantidade=2,
            preco_unitario="45.90",
        )
        self.assertEqual(pedido.recalcular_total(), Decimal("91.80"))
        pedido.refresh_from_db()
        self.assertEqual(pedido.total, Decimal("91.80"))
