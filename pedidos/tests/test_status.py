from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from pedidos.models import Categoria, Pedido, Produto
from pedidos.services import (
    alterar_status,
    atualizar_itens_pedido,
    criar_pedido,
)


class StatusPedidoTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="dono", password="senha-teste"
        )
        self.pizza = Produto.objects.create(
            nome="Margherita", preco="45.90", categoria=Categoria.PIZZA
        )
        self.bebida = Produto.objects.create(
            nome="Água", preco="4.00", categoria=Categoria.BEBIDA
        )

    def _criar(self, **kwargs):
        dados = {
            "itens": [{"ids": [self.pizza.id], "quantidade": 1}],
            "nome": "Ana",
            "telefone": "11999999999",
            "endereco": "Rua A, 1",
        }
        dados.update(kwargs)
        return criar_pedido(**dados)

    def test_status_inicial_de_cliente(self):
        pedido = self._criar()

        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)
        self.assertEqual(pedido.origem, Pedido.Origem.CLIENTE)

    def test_status_inicial_de_balcao(self):
        pedido = self._criar(origem=Pedido.Origem.BALCAO)

        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertEqual(pedido.origem, Pedido.Origem.BALCAO)

    def test_status_inicial_invalido(self):
        with self.assertRaises(ValidationError):
            self._criar(status_inicial=Pedido.Status.ENTREGUE)

    def test_transicoes_validas_ate_entrega(self):
        pedido = self._criar(itens=[{"ids": [self.bebida.id], "quantidade": 1}])

        pedido = alterar_status(
            pedido, Pedido.Status.APROVADO, usuario=self.usuario
        )
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertEqual(pedido.aprovado_por, self.usuario)
        self.assertIsNotNone(pedido.aprovado_em)

        pedido = alterar_status(pedido, Pedido.Status.PREPARANDO)
        pedido = alterar_status(pedido, Pedido.Status.SAIU)
        pedido = alterar_status(pedido, Pedido.Status.ENTREGUE)

        self.assertEqual(pedido.status, Pedido.Status.ENTREGUE)

    def test_transicao_invalida_nao_alterada(self):
        pedido = self._criar()

        with self.assertRaises(ValidationError):
            alterar_status(pedido, Pedido.Status.PREPARANDO)

        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)

    def test_status_final_nao_transiciona(self):
        pedido = self._criar(itens=[{"ids": [self.bebida.id], "quantidade": 1}])
        pedido = alterar_status(pedido, Pedido.Status.APROVADO)
        pedido = alterar_status(pedido, Pedido.Status.PREPARANDO)
        pedido = alterar_status(pedido, Pedido.Status.SAIU)
        pedido = alterar_status(pedido, Pedido.Status.ENTREGUE)

        with self.assertRaises(ValidationError):
            alterar_status(pedido, Pedido.Status.CANCELADO)

    def test_cancelamento_grava_motivo(self):
        pedido = self._criar()

        pedido = alterar_status(
            pedido,
            Pedido.Status.CANCELADO,
            usuario=self.usuario,
            motivo="Endereço fora da área",
        )

        self.assertEqual(pedido.status, Pedido.Status.CANCELADO)
        self.assertEqual(
            pedido.motivo_cancelamento, "Endereço fora da área"
        )

    def test_itens_editaveis_por_status(self):
        pedido = self._criar()
        self.assertTrue(pedido.itens_editaveis)

        pedido = alterar_status(pedido, Pedido.Status.APROVADO)
        self.assertTrue(pedido.itens_editaveis)

        pedido = alterar_status(pedido, Pedido.Status.PREPARANDO)
        self.assertFalse(pedido.itens_editaveis)

    def test_edicao_de_itens_bloqueada_em_preparando(self):
        pedido = self._criar()
        pedido = alterar_status(pedido, Pedido.Status.APROVADO)
        pedido = alterar_status(pedido, Pedido.Status.PREPARANDO)

        with self.assertRaises(ValidationError):
            atualizar_itens_pedido(
                pedido, [{"ids": [self.pizza.id], "quantidade": 2}]
            )

    def test_edicao_recalcula_total_no_servidor(self):
        pedido = self._criar()

        pedido = atualizar_itens_pedido(
            pedido, [{"ids": [self.pizza.id], "quantidade": 2}]
        )

        self.assertEqual(pedido.total, Decimal("91.80"))
        self.assertEqual(pedido.itens.count(), 1)
        self.assertEqual(pedido.itens.get().preco_unitario, Decimal("45.90"))
