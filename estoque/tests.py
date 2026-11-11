from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from estoque.models import FichaTecnica, Ingrediente, MovimentoEstoque
from estoque.services import (
    consumir_pedido,
    estornar_pedido,
    registrar_movimento,
)
from pedidos.models import Categoria, Pedido, Produto
from pedidos.services import alterar_status, atualizar_itens_pedido, criar_pedido


class EstoquePedidoTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="dono-estoque",
            password="senha-teste",
            is_staff=True,
        )
        self.mussarela = Ingrediente.objects.create(
            nome="Mussarela",
            unidade=Ingrediente.Unidade.GRAMA,
            estoque_atual="1000",
            estoque_minimo="100",
        )
        self.calabresa = Ingrediente.objects.create(
            nome="Calabresa",
            unidade=Ingrediente.Unidade.GRAMA,
            estoque_atual="500",
            estoque_minimo="100",
        )
        self.pizza = Produto.objects.create(
            nome="Margherita", preco="45.90", categoria=Categoria.PIZZA
        )
        self.pizza_calabresa = Produto.objects.create(
            nome="Calabresa", preco="49.90", categoria=Categoria.PIZZA
        )
        self.bebida = Produto.objects.create(
            nome="Água", preco="4.00", categoria=Categoria.BEBIDA
        )
        FichaTecnica.objects.create(
            produto=self.pizza,
            ingrediente=self.mussarela,
            quantidade="200",
        )
        FichaTecnica.objects.create(
            produto=self.pizza_calabresa,
            ingrediente=self.calabresa,
            quantidade="200",
        )

    def _criar(self, itens, **kwargs):
        dados = {
            "itens": itens,
            "nome": "Ana",
            "telefone": "11999999999",
            "endereco": "Rua A, 1",
        }
        dados.update(kwargs)
        return criar_pedido(**dados)

    def _aprovar(self, pedido):
        return alterar_status(pedido, Pedido.Status.APROVADO)

    def test_baixa_de_pizza_inteira(self):
        pedido = self._criar([{"ids": [self.pizza.id], "quantidade": 2}])

        self._aprovar(pedido)

        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("600"))
        movimento = MovimentoEstoque.objects.get(
            pedido=pedido, tipo=MovimentoEstoque.Tipo.SAIDA
        )
        self.assertEqual(movimento.quantidade, Decimal("400"))
        self.assertEqual(movimento.saldo_apos, Decimal("600"))

    def test_baixa_de_meia_pizza(self):
        pedido = self._criar(
            [{"ids": [self.pizza.id, self.pizza_calabresa.id], "quantidade": 2}]
        )

        self._aprovar(pedido)

        self.mussarela.refresh_from_db()
        self.calabresa.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("800"))
        self.assertEqual(self.calabresa.estoque_atual, Decimal("300"))

    def test_criacao_de_balcao_ja_consome_estoque(self):
        pedido = self._criar(
            [{"ids": [self.pizza.id], "quantidade": 1}],
            origem=Pedido.Origem.BALCAO,
            usuario=self.staff,
        )

        self.mussarela.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertEqual(self.mussarela.estoque_atual, Decimal("800"))

    def test_estorno_em_cancelamento(self):
        pedido = self._criar([{"ids": [self.pizza.id], "quantidade": 2}])
        pedido = self._aprovar(pedido)
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("600"))

        alterar_status(
            pedido,
            Pedido.Status.CANCELADO,
            motivo="Cliente desistiu",
        )

        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("1000"))
        self.assertTrue(
            MovimentoEstoque.objects.filter(
                pedido=pedido, tipo=MovimentoEstoque.Tipo.ESTORNO
            ).exists()
        )

    def test_estorno_nao_duplica(self):
        pedido = self._criar([{"ids": [self.pizza.id], "quantidade": 2}])
        pedido = self._aprovar(pedido)
        alterar_status(pedido, Pedido.Status.CANCELADO, motivo="Cliente desistiu")

        self.assertEqual(estornar_pedido(pedido), [])

        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("1000"))
        self.assertEqual(
            MovimentoEstoque.objects.filter(
                pedido=pedido, tipo=MovimentoEstoque.Tipo.ESTORNO
            ).count(),
            1,
        )

    def test_cancelamento_apos_preparando_nao_estorna(self):
        pedido = self._criar([{"ids": [self.pizza.id], "quantidade": 1}])
        pedido = self._aprovar(pedido)
        pedido = alterar_status(pedido, Pedido.Status.PREPARANDO)

        alterar_status(pedido, Pedido.Status.CANCELADO, motivo="Perda")

        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("800"))
        self.assertFalse(
            MovimentoEstoque.objects.filter(
                pedido=pedido, tipo=MovimentoEstoque.Tipo.ESTORNO
            ).exists()
        )

    def test_edicao_apos_aprovacao_nao_duplica_baixa(self):
        pedido = self._criar([{"ids": [self.pizza.id], "quantidade": 1}])
        pedido = self._aprovar(pedido)
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("800"))

        pedido = atualizar_itens_pedido(
            pedido, [{"ids": [self.pizza.id], "quantidade": 2}]
        )
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("600"))
        self.assertEqual(pedido.total, Decimal("91.80"))

        atualizar_itens_pedido(
            pedido, [{"ids": [self.pizza.id], "quantidade": 2}]
        )
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("600"))

    def test_produto_sem_ficha_nao_quebra(self):
        pedido = self._criar([{"ids": [self.bebida.id], "quantidade": 3}])

        pedido = self._aprovar(pedido)
        avisos = consumir_pedido(pedido)

        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertTrue(any("sem ficha técnica" in aviso for aviso in avisos))
        self.assertFalse(
            MovimentoEstoque.objects.filter(pedido=pedido).exists()
        )
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("1000"))

    def test_movimento_manual_atualiza_saldo(self):
        movimento = registrar_movimento(
            self.mussarela,
            MovimentoEstoque.Tipo.ENTRADA,
            "250",
            motivo="Compra",
        )

        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("1250"))
        self.assertEqual(movimento.saldo_apos, Decimal("1250"))

    def test_abaixo_minimo(self):
        self.assertFalse(self.mussarela.abaixo_minimo)

        self.mussarela.estoque_atual = Decimal("50")
        self.mussarela.save(update_fields=["estoque_atual"])
        self.mussarela.refresh_from_db()

        self.assertTrue(self.mussarela.abaixo_minimo)


class FichaTecnicaTests(TestCase):
    def setUp(self):
        self.ingrediente = Ingrediente.objects.create(
            nome="Farinha", unidade=Ingrediente.Unidade.GRAMA
        )
        self.produto = Produto.objects.create(
            nome="Pizza", preco="40.00", categoria=Categoria.PIZZA
        )

    def test_quantidade_deve_ser_positiva(self):
        ficha = FichaTecnica(
            produto=self.produto,
            ingrediente=self.ingrediente,
            quantidade="0",
        )

        with self.assertRaises(ValidationError):
            ficha.full_clean()

    def test_unique_together(self):
        FichaTecnica.objects.create(
            produto=self.produto,
            ingrediente=self.ingrediente,
            quantidade="100",
        )
        duplicada = FichaTecnica(
            produto=self.produto,
            ingrediente=self.ingrediente,
            quantidade="50",
        )

        with self.assertRaises(ValidationError):
            duplicada.full_clean()

    def test_quantidade_negativa_rejeitada(self):
        ficha = FichaTecnica(
            produto=self.produto,
            ingrediente=self.ingrediente,
            quantidade="-1",
        )

        with self.assertRaises(ValidationError):
            ficha.full_clean()


class PainelEstoqueTests(TestCase):
    def setUp(self):
        usuario = get_user_model()
        self.staff = usuario.objects.create_user(
            username="dono", password="senha-teste", is_staff=True
        )
        self.cliente = usuario.objects.create_user(
            username="cliente", password="senha-teste"
        )
        self.ingrediente = Ingrediente.objects.create(
            nome="Mussarela",
            unidade=Ingrediente.Unidade.GRAMA,
            estoque_atual="1000",
            estoque_minimo="100",
        )
        self.ingrediente_baixo = Ingrediente.objects.create(
            nome="Calabresa",
            unidade=Ingrediente.Unidade.GRAMA,
            estoque_atual="50",
            estoque_minimo="100",
        )
        self.produto_sem_ficha = Produto.objects.create(
            nome="Pizza sem ficha",
            preco="40.00",
            categoria=Categoria.PIZZA,
        )
        self.produto_com_ficha = Produto.objects.create(
            nome="Pizza completa",
            preco="45.00",
            categoria=Categoria.PIZZA,
        )
        FichaTecnica.objects.create(
            produto=self.produto_com_ficha,
            ingrediente=self.ingrediente,
            quantidade="200",
        )
        self.url_lista = reverse("estoque:lista")
        self.url_ajuste = reverse(
            "estoque:ajustar", args=[self.ingrediente.pk]
        )

    def _postar_ajuste(self, **dados):
        payload = {
            "tipo": MovimentoEstoque.Tipo.ENTRADA,
            "quantidade": "100",
            "motivo": "Compra do fornecedor",
        }
        payload.update(dados)
        return self.client.post(self.url_ajuste, payload)

    def test_lista_exige_staff(self):
        resposta = self.client.get(self.url_lista)
        self.assertEqual(resposta.status_code, 302)

        self.client.force_login(self.cliente)
        resposta = self.client.get(self.url_lista)
        self.assertEqual(resposta.status_code, 302)

        self.client.force_login(self.staff)
        resposta = self.client.get(self.url_lista)
        self.assertEqual(resposta.status_code, 200)

    def test_lista_mostra_ingrediente_abaixo_do_minimo(self):
        self.client.force_login(self.staff)

        resposta = self.client.get(self.url_lista)
        self.assertContains(resposta, "Calabresa")
        self.assertContains(resposta, "Abaixo do mínimo")

        resposta = self.client.get(self.url_lista, {"status": "abaixo"})
        self.assertContains(resposta, "Calabresa")
        self.assertNotContains(resposta, "Mussarela")

    def test_lista_busca_por_nome(self):
        self.client.force_login(self.staff)

        resposta = self.client.get(self.url_lista, {"q": "calab"})
        self.assertContains(resposta, "Calabresa")
        self.assertNotContains(resposta, "Mussarela")

    def test_ajuste_de_entrada_aumenta_saldo_e_registra_movimento(self):
        self.client.force_login(self.staff)

        resposta = self._postar_ajuste(
            tipo=MovimentoEstoque.Tipo.ENTRADA,
            quantidade="250.500",
            motivo="Compra do fornecedor",
        )

        self.assertRedirects(resposta, self.url_lista)
        self.ingrediente.refresh_from_db()
        self.assertEqual(
            self.ingrediente.estoque_atual, Decimal("1250.500")
        )
        movimento = MovimentoEstoque.objects.get()
        self.assertEqual(movimento.tipo, MovimentoEstoque.Tipo.ENTRADA)
        self.assertEqual(movimento.quantidade, Decimal("250.500"))
        self.assertEqual(movimento.saldo_apos, Decimal("1250.500"))
        self.assertEqual(movimento.saldo_apos, self.ingrediente.estoque_atual)
        self.assertEqual(movimento.motivo, "Compra do fornecedor")
        self.assertEqual(movimento.criado_por, self.staff)

    def test_ajuste_exibe_mensagem_com_saldo_antes_e_depois(self):
        self.client.force_login(self.staff)

        resposta = self.client.post(
            self.url_ajuste,
            {
                "tipo": MovimentoEstoque.Tipo.ENTRADA,
                "quantidade": "100",
                "motivo": "Compra do fornecedor",
            },
            follow=True,
        )

        self.assertRedirects(resposta, self.url_lista)
        self.assertContains(resposta, "Saldo: 1000 → 1100 g.")

    def test_ajuste_de_perda_diminui_saldo(self):
        self.client.force_login(self.staff)

        resposta = self._postar_ajuste(
            tipo=MovimentoEstoque.Tipo.PERDA,
            quantidade="100",
            motivo="Quebra de embalagem",
        )

        self.assertRedirects(resposta, self.url_lista)
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("900"))
        movimento = MovimentoEstoque.objects.get()
        self.assertEqual(movimento.tipo, MovimentoEstoque.Tipo.PERDA)
        self.assertEqual(movimento.saldo_apos, Decimal("900"))

    def test_quantidade_invalida_nao_altera_saldo(self):
        self.client.force_login(self.staff)

        for quantidade in ("0", "-1", "abc", ""):
            resposta = self._postar_ajuste(quantidade=quantidade)
            self.assertEqual(resposta.status_code, 200)

        self.assertFalse(MovimentoEstoque.objects.exists())
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("1000"))

    def test_motivo_e_obrigatorio(self):
        self.client.force_login(self.staff)

        resposta = self._postar_ajuste(motivo="   ")

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Informe o motivo do ajuste.")
        self.assertFalse(MovimentoEstoque.objects.exists())
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("1000"))

    def test_movimento_registra_usuario_logado(self):
        self.client.force_login(self.staff)

        self._postar_ajuste()

        self.assertEqual(
            MovimentoEstoque.objects.get().criado_por, self.staff
        )

    def test_saida_e_estorno_nao_sao_permitidos_manualmente(self):
        self.client.force_login(self.staff)

        for tipo in (
            MovimentoEstoque.Tipo.SAIDA,
            MovimentoEstoque.Tipo.ESTORNO,
        ):
            resposta = self._postar_ajuste(tipo=tipo)
            self.assertEqual(resposta.status_code, 200)

        self.assertFalse(MovimentoEstoque.objects.exists())
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("1000"))

    def test_produto_sem_ficha_aparece_como_aviso(self):
        self.client.force_login(self.staff)

        resposta = self.client.get(self.url_lista)

        self.assertContains(resposta, "Pizza sem ficha")
        self.assertContains(resposta, "Produtos sem ficha técnica")
        self.assertIn(
            self.produto_sem_ficha, resposta.context["produtos_sem_ficha"]
        )
        self.assertNotIn(
            self.produto_com_ficha, resposta.context["produtos_sem_ficha"]
        )

    def test_pagina_de_ajuste_exige_staff_e_mostra_saldo(self):
        resposta = self.client.get(self.url_ajuste)
        self.assertEqual(resposta.status_code, 302)

        self.client.force_login(self.cliente)
        resposta = self.client.get(self.url_ajuste)
        self.assertEqual(resposta.status_code, 302)

        self.client.force_login(self.staff)
        resposta = self.client.get(self.url_ajuste)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Saldo antes")
        self.assertContains(resposta, "Mussarela")


class EstoqueAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="senha-teste",
        )
        self.ingrediente = Ingrediente.objects.create(
            nome="Farinha",
            unidade=Ingrediente.Unidade.GRAMA,
            estoque_atual="500",
            estoque_minimo="100",
        )
        self.produto = Produto.objects.create(
            nome="Pizza de teste",
            preco="40.00",
            categoria=Categoria.PIZZA,
        )
        FichaTecnica.objects.create(
            produto=self.produto,
            ingrediente=self.ingrediente,
            quantidade="250",
        )
        self.client.force_login(self.admin)

    def test_admin_de_estoque_abre_sem_erro(self):
        urls = (
            "admin:estoque_ingrediente_changelist",
            "admin:estoque_ingrediente_add",
            "admin:estoque_fichatecnica_changelist",
            "admin:estoque_movimentoestoque_changelist",
        )

        for nome in urls:
            resposta = self.client.get(reverse(nome))
            self.assertEqual(resposta.status_code, 200, nome)

    def test_admin_de_produto_exibe_inline_de_ficha_tecnica(self):
        resposta = self.client.get(
            reverse("admin:pedidos_produto_change", args=[self.produto.pk])
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Fichas técnicas")
        self.assertContains(resposta, "Farinha")
