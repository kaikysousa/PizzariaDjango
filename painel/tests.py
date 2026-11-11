from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from enderecos.models import Condominio
from estoque.models import FichaTecnica, Ingrediente
from pedidos.models import Categoria, Pedido, Produto
from pedidos.services import alterar_status, criar_pedido


class PainelBaseTestCase(TestCase):
    def setUp(self):
        usuarios = get_user_model()
        self.staff = usuarios.objects.create_user(
            username="dono",
            password="senha-teste",
            is_staff=True,
        )
        self.comum = usuarios.objects.create_user(
            username="cliente",
            password="senha-teste",
        )

        self.pizza = Produto.objects.create(
            nome="Margherita", preco="45.90", categoria=Categoria.PIZZA
        )
        self.pizza2 = Produto.objects.create(
            nome="Calabresa", preco="49.90", categoria=Categoria.PIZZA
        )
        self.bebida = Produto.objects.create(
            nome="Água", preco="4.00", categoria=Categoria.BEBIDA
        )

        self.ingrediente = Ingrediente.objects.create(
            nome="Mussarela",
            unidade=Ingrediente.Unidade.GRAMA,
            estoque_atual=Decimal("1000.000"),
            estoque_minimo=Decimal("200.000"),
        )
        self.ficha = FichaTecnica.objects.create(
            produto=self.pizza,
            ingrediente=self.ingrediente,
            quantidade=Decimal("300.000"),
        )

        self.condominio = Condominio.objects.create(
            nome="Edifício Sol",
            endereco="Rua das Flores",
            numero="10",
            bairro="Centro",
            cidade="São Paulo",
            cep="01000-000",
        )

        self.url_dashboard = reverse("painel_dashboard")
        self.url_lista = reverse("painel_pedidos")
        self.url_novo = reverse("painel_pedido_novo")

    def _dados_form(self, **overrides):
        dados = {
            "nome": "Ana Balcão",
            "telefone": "11999998888",
            "condominio": "",
            "endereco": "Rua B, 2",
            "endereco2": "",
            "pagamento": Pedido.Pagamento.PIX,
            "observacoes": "",
            "itens-TOTAL_FORMS": "2",
            "itens-INITIAL_FORMS": "0",
            "itens-MIN_NUM_FORMS": "1",
            "itens-MAX_NUM_FORMS": "1000",
            "itens-0-produto": str(self.pizza.id),
            "itens-0-segundo_produto": "",
            "itens-0-quantidade": "1",
            "itens-1-produto": "",
            "itens-1-segundo_produto": "",
            "itens-1-quantidade": "",
        }
        dados.update(overrides)
        return dados

    def _criar_pendente(self, quantidade=1, produto=None):
        produto = produto or self.pizza
        return criar_pedido(
            itens=[{"ids": [produto.id], "quantidade": quantidade}],
            nome="Cliente",
            telefone="11988887777",
            endereco="Rua C, 3",
        )

    def _post_acao(self, pedido, acao, motivo="", follow=False, **extra):
        dados = {"acao": acao, "motivo": motivo}
        dados.update(extra)
        return self.client.post(
            reverse("painel_pedido_acao", args=[pedido.pk]),
            dados,
            follow=follow,
        )


class AutenticacaoPainelTests(PainelBaseTestCase):
    def test_anonimo_redireciona_para_login(self):
        for url in [
            self.url_dashboard,
            self.url_lista,
            reverse("painel_pedido_novo"),
        ]:
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 302)
            self.assertIn("/admin/login/", resposta.url)

    def test_anonimo_nao_acessa_detalhe(self):
        pedido = self._criar_pendente()

        resposta = self.client.get(
            reverse("painel_pedido_detalhe", args=[pedido.pk])
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/admin/login/", resposta.url)

    def test_usuario_comum_recebe_redirect_ou_403(self):
        self.client.force_login(self.comum)

        resposta = self.client.get(self.url_dashboard)

        self.assertIn(resposta.status_code, (302, 403))

    def test_staff_acessa_dashboard(self):
        self.client.force_login(self.staff)

        resposta = self.client.get(self.url_dashboard)

        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, "painel/dashboard.html")
        self.assertContains(resposta, "Dashboard")


class DashboardTests(PainelBaseTestCase):
    def test_dashboard_mostra_contagem_e_alerta_de_estoque(self):
        self._criar_pendente()
        self.ingrediente.estoque_atual = Decimal("100.000")
        self.ingrediente.save(update_fields=["estoque_atual"])
        self.client.force_login(self.staff)

        resposta = self.client.get(self.url_dashboard)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Mussarela")
        self.assertContains(resposta, "Aguardando aprovação")


class ListaPedidosTests(PainelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)
        self.pendente = self._criar_pendente()
        self.aprovado = criar_pedido(
            itens=[{"ids": [self.bebida.id], "quantidade": 1}],
            nome="Aprovado",
            telefone="11977776666",
            endereco="Rua D, 4",
            origem=Pedido.Origem.BALCAO,
            usuario=self.staff,
        )

    def test_lista_filtra_por_status(self):
        resposta = self.client.get(self.url_lista, {"status": "aprovado"})

        self.assertEqual(resposta.status_code, 200)
        pedidos = list(resposta.context["page_obj"].object_list)
        self.assertEqual([pedido.pk for pedido in pedidos], [self.aprovado.pk])

    def test_lista_busca_por_nome_ou_telefone(self):
        resposta = self.client.get(self.url_lista, {"q": "11988887777"})

        pedidos = list(resposta.context["page_obj"].object_list)
        self.assertEqual([pedido.pk for pedido in pedidos], [self.pendente.pk])


class CriarPedidoTests(PainelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_cria_pedido_manual_com_itens(self):
        resposta = self.client.post(
            self.url_novo,
            self._dados_form(
                **{
                    "itens-0-quantidade": "2",
                }
            ),
        )

        pedido = Pedido.objects.latest("pk")
        self.assertRedirects(
            resposta, reverse("painel_pedido_detalhe", args=[pedido.pk])
        )
        self.assertEqual(pedido.origem, Pedido.Origem.BALCAO)
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertEqual(pedido.itens.count(), 1)
        self.assertEqual(pedido.itens.get().quantidade, 2)
        self.assertEqual(pedido.aprovado_por, self.staff)

    def test_pedido_manual_nasce_aprovado(self):
        self.client.post(self.url_novo, self._dados_form())

        pedido = Pedido.objects.latest("pk")
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)

    def test_total_ignora_valor_enviado(self):
        self.client.post(
            self.url_novo,
            self._dados_form(
                **{
                    "total": "1.00",
                    "itens-0-quantidade": "2",
                }
            ),
        )

        pedido = Pedido.objects.latest("pk")
        self.assertEqual(pedido.total, Decimal("91.80"))

    def test_condominio_preenche_endereco_no_servidor(self):
        self.client.post(
            self.url_novo,
            self._dados_form(
                **{
                    "condominio": str(self.condominio.id),
                    "endereco": "",
                }
            ),
        )

        pedido = Pedido.objects.latest("pk")
        self.assertEqual(pedido.condominio, self.condominio)
        self.assertEqual(pedido.endereco, self.condominio.endereco_completo)

    def test_meia_pizza_invalida_preserva_dados(self):
        resposta = self.client.post(
            self.url_novo,
            self._dados_form(
                **{
                    "nome": "Nome digitado",
                    "itens-0-segundo_produto": str(self.bebida.id),
                }
            ),
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Meia pizza só pode ser montada com pizzas.")
        self.assertContains(resposta, "Nome digitado")
        self.assertFalse(Pedido.objects.exists())

    def test_sem_itens_nao_cria_pedido(self):
        resposta = self.client.post(
            self.url_novo,
            self._dados_form(
                **{
                    "itens-0-produto": "",
                    "itens-0-quantidade": "",
                }
            ),
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Adicione pelo menos um item")
        self.assertFalse(Pedido.objects.exists())


class EditarPedidoTests(PainelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_edita_pedido_pendente_e_recalcula_total(self):
        pedido = self._criar_pendente()

        resposta = self.client.post(
            reverse("painel_pedido_editar", args=[pedido.pk]),
            self._dados_form(
                **{
                    "nome": "Nome novo",
                    "itens-0-quantidade": "2",
                }
            ),
        )

        pedido.refresh_from_db()
        self.assertRedirects(
            resposta, reverse("painel_pedido_detalhe", args=[pedido.pk])
        )
        self.assertEqual(pedido.nome, "Nome novo")
        self.assertEqual(pedido.total, Decimal("91.80"))
        self.assertEqual(pedido.itens.get().quantidade, 2)

    def test_itens_travados_apos_preparando(self):
        pedido = self._criar_pendente()
        pedido = alterar_status(pedido, Pedido.Status.APROVADO, usuario=self.staff)
        pedido = alterar_status(pedido, Pedido.Status.PREPARANDO)

        resposta = self.client.post(
            reverse("painel_pedido_editar", args=[pedido.pk]),
            self._dados_form(
                **{
                    "nome": "Nome alterado",
                    "itens-0-produto": str(self.bebida.id),
                    "itens-0-quantidade": "5",
                }
            ),
        )

        pedido.refresh_from_db()
        self.assertRedirects(
            resposta, reverse("painel_pedido_detalhe", args=[pedido.pk])
        )
        self.assertEqual(pedido.nome, "Nome alterado")
        self.assertEqual(pedido.itens.count(), 1)
        self.assertEqual(pedido.itens.get().produto, self.pizza)
        self.assertEqual(pedido.itens.get().quantidade, 1)

    def test_edicao_de_itens_aprovados_reprocessa_estoque(self):
        pedido = self._criar_pendente()
        self._post_acao(pedido, "aprovar")
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("700.000"))

        resposta = self.client.post(
            reverse("painel_pedido_editar", args=[pedido.pk]),
            self._dados_form(
                **{
                    "itens-0-quantidade": "2",
                }
            ),
        )

        pedido.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.assertRedirects(
            resposta, reverse("painel_pedido_detalhe", args=[pedido.pk])
        )
        self.assertEqual(pedido.total, Decimal("91.80"))
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("400.000"))

    def test_formulario_de_edicao_renderiza_itens(self):
        pedido = self._criar_pendente()

        resposta = self.client.get(
            reverse("painel_pedido_editar", args=[pedido.pk])
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Margherita")

    def test_edicao_preserva_condominio_inativo(self):
        pedido = self._criar_pendente()
        pedido.condominio = self.condominio
        pedido.save(update_fields=["condominio"])
        self.condominio.ativo = False
        self.condominio.save(update_fields=["ativo"])

        resposta = self.client.get(
            reverse("painel_pedido_editar", args=[pedido.pk])
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(
            self.condominio,
            resposta.context["form"].fields["condominio"].queryset,
        )

    def test_edicao_mostra_itens_em_leitura_apos_preparando(self):
        pedido = self._criar_pendente()
        pedido = alterar_status(pedido, Pedido.Status.APROVADO, usuario=self.staff)
        alterar_status(pedido, Pedido.Status.PREPARANDO)

        resposta = self.client.get(
            reverse("painel_pedido_editar", args=[pedido.pk])
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Itens em modo leitura")
        self.assertNotContains(resposta, "itens-0-produto")


class AcoesStatusTests(PainelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_detalhe_mostra_somente_transicoes_validas(self):
        pedido = self._criar_pendente()

        resposta = self.client.get(
            reverse("painel_pedido_detalhe", args=[pedido.pk])
        )

        self.assertContains(resposta, "Aprovar pedido")
        self.assertContains(resposta, "Recusar pedido")
        self.assertNotContains(resposta, "Iniciar preparo")
        self.assertContains(
            resposta, reverse("recibo", args=[pedido.token])
        )

        pedido = alterar_status(pedido, Pedido.Status.APROVADO, usuario=self.staff)
        pedido = alterar_status(pedido, Pedido.Status.PREPARANDO)
        resposta = self.client.get(
            reverse("painel_pedido_detalhe", args=[pedido.pk])
        )

        self.assertContains(resposta, "Sair para entrega")
        self.assertContains(resposta, "Cancelar pedido")
        self.assertNotContains(resposta, "Aprovar pedido")

    def test_aprova_pedido_e_baixa_estoque(self):
        pedido = self._criar_pendente(quantidade=2)

        resposta = self._post_acao(pedido, "aprovar")

        pedido.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.assertRedirects(
            resposta, reverse("painel_pedido_detalhe", args=[pedido.pk])
        )
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
        self.assertEqual(pedido.aprovado_por, self.staff)
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("400.000"))

    def test_recusa_exige_motivo(self):
        pedido = self._criar_pendente()

        resposta = self._post_acao(pedido, "recusar", motivo="", follow=True)

        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)
        self.assertContains(resposta, "Informe o motivo")

    def test_recusa_com_motivo_cancela(self):
        pedido = self._criar_pendente()

        self._post_acao(pedido, "recusar", motivo="Fora da área")

        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.CANCELADO)
        self.assertEqual(pedido.motivo_cancelamento, "Fora da área")

    def test_transicao_invalida_nao_altera(self):
        pedido = self._criar_pendente()

        resposta = self._post_acao(pedido, "preparar", follow=True)

        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)
        self.assertContains(resposta, "Transição inválida")

    def test_cancelamento_apos_aprovacao_estorna_estoque(self):
        pedido = self._criar_pendente(quantidade=2)
        self._post_acao(pedido, "aprovar")
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("400.000"))

        self._post_acao(pedido, "cancelar", motivo="Cliente desistiu")

        pedido.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.CANCELADO)
        self.assertEqual(self.ingrediente.estoque_atual, Decimal("1000.000"))

    def test_avanca_status_ate_entrega(self):
        pedido = self._criar_pendente(produto=self.bebida)
        for acao in ["aprovar", "preparar", "sair", "entregar"]:
            self._post_acao(pedido, acao)
            pedido.refresh_from_db()

        self.assertEqual(pedido.status, Pedido.Status.ENTREGUE)


class CsrfPainelTests(PainelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = Client(enforce_csrf_checks=True)
        self.cliente.force_login(self.staff)

    def test_acao_sem_csrf_e_rejeitada(self):
        pedido = self._criar_pendente()

        resposta = self.cliente.post(
            reverse("painel_pedido_acao", args=[pedido.pk]),
            {"acao": "aprovar"},
        )

        pedido.refresh_from_db()
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)

    def test_criacao_sem_csrf_e_rejeitada(self):
        resposta = self.cliente.post(self.url_novo, self._dados_form())

        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(Pedido.objects.exists())

    def test_acao_com_csrf_funciona(self):
        pedido = self._criar_pendente()
        self.cliente.get(reverse("painel_pedido_detalhe", args=[pedido.pk]))
        token = self.cliente.cookies["csrftoken"].value

        resposta = self.cliente.post(
            reverse("painel_pedido_acao", args=[pedido.pk]),
            {"acao": "aprovar", "csrfmiddlewaretoken": token},
        )

        pedido.refresh_from_db()
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(pedido.status, Pedido.Status.APROVADO)
