"""Testes E2E do fluxo de gestão: checkout, painel, estoque e recibo.

Cada classe cobre um cenário do prompt de testes E2E e usa o banco de teste
isolado do Django. Os dados nascem no ``setUp`` e nenhum teste depende da
ordem de execução.
"""

import json
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.test import Client, TestCase
from django.urls import reverse

from enderecos.models import Condominio
from estoque.models import FichaTecnica, Ingrediente, MovimentoEstoque
from pedidos.models import Categoria, Pedido, Produto
from pedidos.services import alterar_status, atualizar_itens_pedido, criar_pedido


class GestaoE2EBaseTestCase(TestCase):
    def setUp(self):
        usuarios = get_user_model()
        self.staff = usuarios.objects.create_user(
            username="dono-e2e",
            password="senha-teste",
            is_staff=True,
        )
        self.comum = usuarios.objects.create_user(
            username="cliente-e2e",
            password="senha-teste",
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

        self.mussarela = Ingrediente.objects.create(
            nome="Mussarela",
            unidade=Ingrediente.Unidade.GRAMA,
            estoque_atual=Decimal("1000.000"),
            estoque_minimo=Decimal("200.000"),
        )
        self.calabresa = Ingrediente.objects.create(
            nome="Calabresa",
            unidade=Ingrediente.Unidade.GRAMA,
            estoque_atual=Decimal("600.000"),
            estoque_minimo=Decimal("100.000"),
        )
        FichaTecnica.objects.create(
            produto=self.pizza,
            ingrediente=self.mussarela,
            quantidade=Decimal("300.000"),
        )
        FichaTecnica.objects.create(
            produto=self.pizza_calabresa,
            ingrediente=self.calabresa,
            quantidade=Decimal("250.000"),
        )

        self.condominio = Condominio.objects.create(
            nome="Edifício Aurora",
            endereco="Rua das Flores",
            numero="100",
            bairro="Centro",
            cidade="São Paulo",
            cep="01000-000",
            referencia="Portaria azul",
        )

    def _login_staff(self):
        self.client.force_login(self.staff)

    def _revisar_carrinho(self, itens):
        resposta = self.client.post(
            reverse("revisar_pedido"),
            {"carrinho": json.dumps({"itens": itens})},
        )
        self.assertRedirects(resposta, reverse("checkout"))

    def _token_checkout(self):
        resposta = self.client.get(reverse("checkout"))
        self.assertEqual(resposta.status_code, 200)
        return self.client.session["checkout_token"]

    def _dados_checkout(self, **overrides):
        dados = {
            "nome": "Ana Cliente",
            "telefone": "(11) 99999-9999",
            "condominio": "",
            "endereco": "Rua A, 1",
            "endereco2": "Apto 2",
            "observacoes": "Sem cebola",
            "pagamento": Pedido.Pagamento.PIX,
        }
        dados.update(overrides)
        return dados

    def _enviar_checkout(self, **overrides):
        dados = self._dados_checkout(**overrides)
        dados["checkout_token"] = self._token_checkout()
        return self.client.post(reverse("checkout"), dados)

    def _criar_pedido_cliente(self, itens=None, **overrides):
        dados = {
            "itens": itens or [{"ids": [self.pizza.id], "quantidade": 1}],
            "nome": "Ana Cliente",
            "telefone": "11999999999",
            "endereco": "Rua A, 1",
        }
        dados.update(overrides)
        return criar_pedido(**dados)

    def _dados_form_pedido(self, linhas=None, **overrides):
        linhas = linhas or [
            {"produto": self.pizza, "segundo_produto": None, "quantidade": 1}
        ]
        dados = {
            "nome": "Cliente Balcão",
            "telefone": "11999998888",
            "condominio": "",
            "endereco": "Rua B, 2",
            "endereco2": "",
            "pagamento": Pedido.Pagamento.PIX,
            "observacoes": "Retirada no balcão",
            "itens-TOTAL_FORMS": str(len(linhas)),
            "itens-INITIAL_FORMS": "0",
            "itens-MIN_NUM_FORMS": "1",
            "itens-MAX_NUM_FORMS": "1000",
        }
        for indice, linha in enumerate(linhas):
            produto = linha.get("produto")
            segundo = linha.get("segundo_produto")
            dados[f"itens-{indice}-produto"] = str(produto.pk) if produto else ""
            dados[f"itens-{indice}-segundo_produto"] = (
                str(segundo.pk) if segundo else ""
            )
            dados[f"itens-{indice}-quantidade"] = str(
                linha.get("quantidade") or ""
            )
        dados.update(overrides)
        return dados

    def _post_acao(self, pedido, acao, motivo="", follow=False):
        return self.client.post(
            reverse("painel_pedido_acao", args=[pedido.pk]),
            {"acao": acao, "motivo": motivo},
            follow=follow,
        )

    def _url_detalhe(self, pedido):
        return reverse("painel_pedido_detalhe", args=[pedido.pk])

    def _url_acompanhar(self, pedido):
        return reverse("acompanhar_pedido", args=[pedido.token])


class CheckoutCondominioE2ETests(GestaoE2EBaseTestCase):
    def test_cliente_com_condominio_aguarda_aprovacao_sem_baixar_estoque(self):
        self._revisar_carrinho([{"ids": [self.pizza.id], "quantidade": 1}])

        resposta = self._enviar_checkout(
            condominio=str(self.condominio.pk), endereco=""
        )

        self.assertEqual(resposta.status_code, 302)
        pedido = Pedido.objects.get()
        self.assertRedirects(resposta, self._url_acompanhar(pedido))
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)
        self.assertEqual(pedido.origem, Pedido.Origem.CLIENTE)
        self.assertEqual(pedido.condominio, self.condominio)
        self.assertEqual(pedido.endereco, self.condominio.endereco_completo)
        self.assertEqual(pedido.total, Decimal("45.90"))
        self.assertNotIn("carrinho", self.client.session)

        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("1000.000"))
        self.assertFalse(MovimentoEstoque.objects.filter(pedido=pedido).exists())

        pagina = self.client.get(self._url_acompanhar(pedido))

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, "Aguardando aprovação")
        self.assertContains(pagina, self.condominio.nome)
        self.assertContains(pagina, self.condominio.endereco_completo)
        self.assertNotContains(pagina, "Ver recibo")


class AprovacaoEstoqueE2ETests(GestaoE2EBaseTestCase):
    def test_aprovacao_baixa_estoque_registra_saida_e_libera_recibo(self):
        pedido = self._criar_pedido_cliente(
            [{"ids": [self.pizza.id], "quantidade": 2}]
        )
        self._login_staff()

        resposta = self._post_acao(pedido, "aprovar")

        self.assertRedirects(resposta, self._url_detalhe(pedido))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertEqual(pedido.aprovado_por, self.staff)
        self.assertIsNotNone(pedido.aprovado_em)

        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("400.000"))
        movimento = MovimentoEstoque.objects.get(pedido=pedido)
        self.assertEqual(movimento.tipo, MovimentoEstoque.Tipo.SAIDA)
        self.assertEqual(movimento.quantidade, Decimal("600.000"))
        self.assertEqual(movimento.saldo_apos, Decimal("400.000"))
        self.assertEqual(movimento.criado_por, self.staff)

        # Reprocessar a aprovação não duplica a baixa.
        self._post_acao(pedido, "aprovar")
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("400.000"))
        self.assertEqual(MovimentoEstoque.objects.filter(pedido=pedido).count(), 1)

        pagina = self.client.get(self._url_acompanhar(pedido))
        self.assertContains(pagina, "Aprovado")
        self.assertContains(pagina, "Ver recibo")
        self.assertContains(pagina, reverse("recibo", args=[pedido.token]))

        recibo = self.client.get(reverse("recibo", args=[pedido.token]))
        self.assertEqual(recibo.status_code, 200)
        self.assertContains(recibo, f"Pedido #{pedido.pk}")
        self.assertContains(recibo, "Margherita")
        self.assertContains(recibo, "91,80")
        self.assertIn("noindex", recibo["X-Robots-Tag"])


class MeiaPizzaE2ETests(GestaoE2EBaseTestCase):
    def test_meia_pizza_consome_metade_da_ficha_de_cada_sabor(self):
        self._revisar_carrinho(
            [
                {
                    "ids": [self.pizza.id, self.pizza_calabresa.id],
                    "quantidade": 2,
                }
            ]
        )

        resposta = self._enviar_checkout()

        pedido = Pedido.objects.get()
        self.assertRedirects(resposta, self._url_acompanhar(pedido))
        item = pedido.itens.get()
        self.assertEqual(item.produto, self.pizza)
        self.assertEqual(item.segundo_produto, self.pizza_calabresa)
        self.assertEqual(item.preco_unitario, Decimal("47.90"))
        self.assertEqual(item.subtotal, Decimal("95.80"))
        self.assertEqual(pedido.total, Decimal("95.80"))

        self._login_staff()
        self._post_acao(pedido, "aprovar")

        self.mussarela.refresh_from_db()
        self.calabresa.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("700.000"))
        self.assertEqual(self.calabresa.estoque_atual, Decimal("350.000"))

        saida_mussarela = MovimentoEstoque.objects.get(
            pedido=pedido, ingrediente=self.mussarela
        )
        saida_calabresa = MovimentoEstoque.objects.get(
            pedido=pedido, ingrediente=self.calabresa
        )
        self.assertEqual(saida_mussarela.quantidade, Decimal("300.000"))
        self.assertEqual(saida_mussarela.saldo_apos, Decimal("700.000"))
        self.assertEqual(saida_calabresa.quantidade, Decimal("250.000"))
        self.assertEqual(saida_calabresa.saldo_apos, Decimal("350.000"))


class CancelamentoE2ETests(GestaoE2EBaseTestCase):
    def test_cancelamento_apos_aprovacao_estorna_estoque_e_mostra_motivo(self):
        motivo = "Cliente desistiu do pedido"
        pedido = self._criar_pedido_cliente(
            [{"ids": [self.pizza.id], "quantidade": 2}]
        )
        self._login_staff()
        self._post_acao(pedido, "aprovar")
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("400.000"))

        resposta = self._post_acao(pedido, "cancelar", motivo=motivo)

        self.assertRedirects(resposta, self._url_detalhe(pedido))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.CANCELADO)
        self.assertEqual(pedido.motivo_cancelamento, motivo)
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("1000.000"))

        estornos = MovimentoEstoque.objects.filter(
            pedido=pedido, tipo=MovimentoEstoque.Tipo.ESTORNO
        )
        self.assertEqual(estornos.count(), 1)
        self.assertEqual(estornos.get().quantidade, Decimal("600.000"))

        detalhe = self.client.get(self._url_detalhe(pedido))
        self.assertContains(detalhe, "Motivo do cancelamento")
        self.assertContains(detalhe, motivo)

        acompanhar = self.client.get(self._url_acompanhar(pedido))
        self.assertContains(acompanhar, motivo)
        self.assertContains(acompanhar, "cancelado")
        self.assertNotContains(acompanhar, "Ver recibo")


class PedidoManualE2ETests(GestaoE2EBaseTestCase):
    def test_staff_cria_pedido_de_balcao_aprovado_e_estoque_baixa(self):
        self._login_staff()

        resposta = self.client.post(
            reverse("painel_pedido_novo"),
            self._dados_form_pedido(
                [
                    {"produto": self.pizza, "quantidade": 2},
                    {"produto": self.bebida, "quantidade": 1},
                ]
            ),
        )

        pedido = Pedido.objects.latest("pk")
        self.assertRedirects(resposta, self._url_detalhe(pedido))
        self.assertEqual(pedido.origem, Pedido.Origem.BALCAO)
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertEqual(pedido.aprovado_por, self.staff)
        self.assertIsNotNone(pedido.aprovado_em)
        self.assertEqual(pedido.itens.count(), 2)
        self.assertEqual(pedido.total, Decimal("95.80"))

        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("400.000"))

        movimentos = MovimentoEstoque.objects.filter(pedido=pedido)
        self.assertEqual(movimentos.count(), 1)
        movimento = movimentos.get()
        self.assertEqual(movimento.tipo, MovimentoEstoque.Tipo.SAIDA)
        self.assertEqual(movimento.quantidade, Decimal("600.000"))
        self.assertEqual(movimento.saldo_apos, Decimal("400.000"))

        detalhe = self.client.get(self._url_detalhe(pedido))
        self.assertContains(detalhe, "Balcão")
        self.assertContains(detalhe, "Aprovado")


class EdicaoItensE2ETests(GestaoE2EBaseTestCase):
    def test_edicao_aprovada_estorna_e_reaplica_sem_duplicar_movimento(self):
        pedido = self._criar_pedido_cliente()
        self._login_staff()
        self._post_acao(pedido, "aprovar")
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("700.000"))

        dados = self._dados_form_pedido(
            [{"produto": self.pizza, "quantidade": 2}]
        )
        resposta = self.client.post(
            reverse("painel_pedido_editar", args=[pedido.pk]), dados
        )

        self.assertRedirects(resposta, self._url_detalhe(pedido))
        pedido.refresh_from_db()
        self.assertEqual(pedido.total, Decimal("91.80"))
        self.assertEqual(pedido.itens.get().quantidade, 2)
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("400.000"))

        saidas = MovimentoEstoque.objects.filter(
            pedido=pedido, tipo=MovimentoEstoque.Tipo.SAIDA
        )
        estornos = MovimentoEstoque.objects.filter(
            pedido=pedido, tipo=MovimentoEstoque.Tipo.ESTORNO
        )
        self.assertEqual(
            saidas.aggregate(total=Sum("quantidade"))["total"],
            Decimal("900.000"),
        )
        self.assertEqual(
            estornos.aggregate(total=Sum("quantidade"))["total"],
            Decimal("300.000"),
        )
        self.assertEqual(MovimentoEstoque.objects.filter(pedido=pedido).count(), 3)

        # Reenviar exatamente os mesmos itens não cria movimento novo.
        resposta = self.client.post(
            reverse("painel_pedido_editar", args=[pedido.pk]), dados
        )

        self.assertRedirects(resposta, self._url_detalhe(pedido))
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("400.000"))
        self.assertEqual(MovimentoEstoque.objects.filter(pedido=pedido).count(), 3)


class BloqueioAposPreparandoE2ETests(GestaoE2EBaseTestCase):
    def test_itens_travados_mas_status_e_observacao_continuam_permitidos(self):
        pedido = self._criar_pedido_cliente()
        self._login_staff()
        self._post_acao(pedido, "aprovar")
        self._post_acao(pedido, "preparar")
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.PREPARANDO)
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("700.000"))

        formulario = self.client.get(
            reverse("painel_pedido_editar", args=[pedido.pk])
        )
        self.assertContains(formulario, "Itens em modo leitura")

        resposta = self.client.post(
            reverse("painel_pedido_editar", args=[pedido.pk]),
            self._dados_form_pedido(
                [{"produto": self.bebida, "quantidade": 5}],
                nome="Nome Atualizado",
                observacoes="Cliente pediu guardanapos",
            ),
        )

        self.assertRedirects(resposta, self._url_detalhe(pedido))
        pedido.refresh_from_db()
        self.assertEqual(pedido.nome, "Nome Atualizado")
        self.assertEqual(pedido.observacoes, "Cliente pediu guardanapos")
        self.assertEqual(pedido.status, Pedido.Status.PREPARANDO)
        self.assertEqual(pedido.total, Decimal("45.90"))
        item = pedido.itens.get()
        self.assertEqual(item.produto, self.pizza)
        self.assertEqual(item.quantidade, 1)
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("700.000"))
        self.assertEqual(MovimentoEstoque.objects.filter(pedido=pedido).count(), 1)

        with self.assertRaises(ValidationError):
            atualizar_itens_pedido(
                pedido, [{"ids": [self.bebida.id], "quantidade": 5}]
            )

        resposta = self._post_acao(pedido, "sair")
        self.assertRedirects(resposta, self._url_detalhe(pedido))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.SAIU)


class EstoqueBaixoE2ETests(GestaoE2EBaseTestCase):
    def test_baixa_por_aprovacao_dispara_alerta_no_dashboard_e_no_estoque(self):
        self._login_staff()
        painel = self.client.get(reverse("painel_dashboard"))
        self.assertNotContains(painel, "Mussarela")

        pedido = self._criar_pedido_cliente(
            [{"ids": [self.pizza.id], "quantidade": 3}]
        )
        self._post_acao(pedido, "aprovar")
        self.mussarela.refresh_from_db()
        self.assertEqual(self.mussarela.estoque_atual, Decimal("100.000"))
        self.assertTrue(self.mussarela.abaixo_minimo)

        painel = self.client.get(reverse("painel_dashboard"))
        self.assertContains(painel, "Ingredientes abaixo do mínimo")
        self.assertContains(painel, "Mussarela")

        lista = self.client.get(reverse("estoque:lista"), {"status": "abaixo"})
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(lista.context["total_abaixo_minimo"], 1)
        self.assertContains(lista, "Mussarela")
        self.assertContains(lista, "Abaixo do mínimo")


class FluxoStatusE2ETests(GestaoE2EBaseTestCase):
    def test_fluxo_valido_e_transicoes_invalidas_rejeitadas(self):
        self._login_staff()
        pedido = self._criar_pedido_cliente()

        resposta = self._post_acao(pedido, "preparar", follow=True)
        self.assertContains(resposta, "Transição inválida")
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)

        transicoes = [
            ("aprovar", Pedido.Status.APROVADO),
            ("preparar", Pedido.Status.PREPARANDO),
            ("sair", Pedido.Status.SAIU),
            ("entregar", Pedido.Status.ENTREGUE),
        ]
        for acao, esperado in transicoes:
            resposta = self._post_acao(pedido, acao)
            self.assertRedirects(resposta, self._url_detalhe(pedido))
            pedido.refresh_from_db()
            self.assertEqual(pedido.status, esperado, acao)

        resposta = self._post_acao(
            pedido, "cancelar", motivo="Não pode mais", follow=True
        )
        self.assertContains(resposta, "Transição inválida")
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.ENTREGUE)

        cancelado = self._criar_pedido_cliente()
        self._post_acao(cancelado, "aprovar")
        self._post_acao(cancelado, "cancelar", motivo="Fora da área")
        resposta = self._post_acao(cancelado, "aprovar", follow=True)
        self.assertContains(resposta, "Transição inválida")
        cancelado.refresh_from_db()
        self.assertEqual(cancelado.status, Pedido.Status.CANCELADO)


class SegurancaE2ETests(GestaoE2EBaseTestCase):
    def test_anonimo_e_usuario_comum_nao_acessam_painel_nem_acao(self):
        pedido = self._criar_pedido_cliente()
        urls = [
            reverse("painel_dashboard"),
            reverse("painel_pedidos"),
            reverse("painel_pedido_novo"),
            self._url_detalhe(pedido),
            reverse("painel_pedido_editar", args=[pedido.pk]),
            reverse("estoque:lista"),
        ]

        for url in urls:
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 302, url)
            self.assertIn("/admin/login/", resposta.url, url)

        self.client.force_login(self.comum)
        for url in urls:
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 302, url)
            self.assertIn("/admin/login/", resposta.url, url)

        resposta = self.client.post(
            reverse("painel_pedido_acao", args=[pedido.pk]),
            {"acao": "aprovar"},
        )
        self.assertEqual(resposta.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)

    def test_token_de_um_pedido_nao_vaza_dados_de_outro(self):
        pedido_a = self._criar_pedido_cliente(
            nome="Cliente Alfa", endereco="Rua Alfa, 1"
        )
        pedido_b = self._criar_pedido_cliente(
            nome="Cliente Beta", endereco="Rua Beta, 2"
        )
        alterar_status(pedido_a, Pedido.Status.APROVADO, usuario=self.staff)

        pagina_a = self.client.get(self._url_acompanhar(pedido_a))

        self.assertContains(pagina_a, "Cliente Alfa")
        self.assertContains(pagina_a, "Rua Alfa, 1")
        self.assertContains(pagina_a, reverse("recibo", args=[pedido_a.token]))
        self.assertNotContains(pagina_a, "Cliente Beta")
        self.assertNotContains(pagina_a, "Rua Beta, 2")
        self.assertNotContains(pagina_a, reverse("recibo", args=[pedido_b.token]))

        recibo_a = self.client.get(reverse("recibo", args=[pedido_a.token]))
        self.assertContains(recibo_a, "Cliente Alfa")
        self.assertNotContains(recibo_a, "Cliente Beta")

        resposta = self.client.get(
            reverse("acompanhar_pedido", args=[uuid.uuid4()])
        )
        self.assertEqual(resposta.status_code, 404)

    def test_csrf_protege_acao_do_painel_e_revisao_do_carrinho(self):
        pedido = self._criar_pedido_cliente()

        cliente_csrf = Client(enforce_csrf_checks=True)
        cliente_csrf.force_login(self.staff)
        resposta = cliente_csrf.post(
            reverse("painel_pedido_acao", args=[pedido.pk]),
            {"acao": "aprovar"},
        )
        self.assertEqual(resposta.status_code, 403)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)

        anonimo = Client(enforce_csrf_checks=True)
        resposta = anonimo.post(
            reverse("revisar_pedido"),
            {
                "carrinho": json.dumps(
                    {"itens": [{"ids": [self.pizza.id], "quantidade": 1}]}
                )
            },
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertNotIn("carrinho", anonimo.session)

        cliente_csrf.get(self._url_detalhe(pedido))
        token = cliente_csrf.cookies["csrftoken"].value
        resposta = cliente_csrf.post(
            reverse("painel_pedido_acao", args=[pedido.pk]),
            {"acao": "aprovar", "csrfmiddlewaretoken": token},
        )

        self.assertEqual(resposta.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
