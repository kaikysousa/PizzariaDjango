import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from enderecos.models import Condominio
from pedidos.models import Categoria, Pedido, Produto
from pedidos.services import alterar_status, criar_pedido

ENDERECO_COMPLETO = (
    "Rua das Flores, 100 - Centro - São Paulo - CEP 01000-000"
)


class CondominioCheckoutTests(TestCase):
    def setUp(self):
        self.pizza = Produto.objects.create(
            nome="Margherita", preco="45.90", categoria=Categoria.PIZZA
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
        self.condominio_inativo = Condominio.objects.create(
            nome="Edifício Fechado",
            endereco="Rua Sem Saída",
            numero="200",
            bairro="Centro",
            cidade="São Paulo",
            ativo=False,
        )
        self.usuario = get_user_model().objects.create_user(
            username="dono", password="senha-teste"
        )
        self.dados = {
            "nome": "Ana",
            "telefone": "(11) 99999-9999",
            "endereco": "Rua A, 1",
            "endereco2": "Apto 2",
            "observacoes": "Sem cebola",
            "pagamento": "pix",
        }

    def _revisar(self):
        return self.client.post(
            reverse("revisar_pedido"),
            {
                "carrinho": json.dumps(
                    {
                        "itens": [
                            {"ids": [self.pizza.id], "quantidade": 1}
                        ]
                    }
                )
            },
        )

    def _checkout_token(self):
        self.client.get(reverse("checkout"))
        return self.client.session["checkout_token"]

    def _enviar(self, **kwargs):
        self._revisar()
        dados = dict(self.dados, checkout_token=self._checkout_token())
        dados.update(kwargs)
        return self.client.post(reverse("checkout"), dados)

    def _pedido(self, **kwargs):
        dados = {
            "itens": [{"ids": [self.pizza.id], "quantidade": 1}],
            "nome": "Ana",
            "telefone": "11999999999",
            "endereco": "Rua A, 1",
        }
        dados.update(kwargs)
        return criar_pedido(**dados)

    def test_checkout_mostra_apenas_condominios_ativos(self):
        self._revisar()
        response = self.client.get(reverse("checkout"))

        self.assertContains(response, self.condominio.nome)
        self.assertNotContains(response, self.condominio_inativo.nome)

    def test_checkout_exibe_texto_de_ajuda_do_condominio(self):
        self._revisar()
        response = self.client.get(reverse("checkout"))

        self.assertContains(
            response,
            "Selecione o condomínio para preencher o endereço automaticamente.",
        )

    def test_widget_inclui_dados_do_endereco_nas_opcoes(self):
        self._revisar()
        response = self.client.get(reverse("checkout"))
        html = response.content.decode()

        self.assertIn('data-endereco="Rua das Flores"', html)
        self.assertIn('data-numero="100"', html)
        self.assertIn('data-bairro="Centro"', html)
        self.assertIn('data-cidade="São Paulo"', html)
        self.assertIn('data-cep="01000-000"', html)
        self.assertIn('data-referencia="Portaria azul"', html)

    def test_form_salva_condominio(self):
        self._enviar(condominio=self.condominio.pk)

        pedido = Pedido.objects.get()
        self.assertEqual(pedido.condominio, self.condominio)
        self.assertEqual(pedido.endereco, "Rua A, 1")

    def test_endereco_vazio_preenchido_pelo_condominio(self):
        self._enviar(condominio=self.condominio.pk, endereco="")

        pedido = Pedido.objects.get()
        self.assertEqual(pedido.condominio, self.condominio)
        self.assertEqual(pedido.endereco, ENDERECO_COMPLETO)

    def test_endereco_manual_preservado(self):
        self._enviar(
            condominio=self.condominio.pk, endereco="Rua B, 9 - Fundos"
        )

        pedido = Pedido.objects.get()
        self.assertEqual(pedido.endereco, "Rua B, 9 - Fundos")

    def test_endereco_vazio_sem_condominio_gera_erro(self):
        response = self._enviar(endereco="")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(
            response, "Informe o endereço ou selecione um condomínio."
        )

    def test_condominio_inativo_e_rejeitado(self):
        response = self._enviar(
            condominio=self.condominio_inativo.pk, endereco=""
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_pedido_de_cliente_nasce_aguardando_aprovacao(self):
        self._enviar()

        pedido = Pedido.objects.get()
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_APROVACAO)
        self.assertEqual(pedido.origem, Pedido.Origem.CLIENTE)

    def test_redireciona_para_acompanhamento(self):
        response = self._enviar()

        pedido = Pedido.objects.get()
        self.assertRedirects(
            response,
            reverse("acompanhar_pedido", kwargs={"token": pedido.token}),
        )

    def test_acompanhamento_mostra_status_correto(self):
        pedido = self._pedido()

        response = self.client.get(
            reverse("acompanhar_pedido", kwargs={"token": pedido.token})
        )

        self.assertContains(response, "Aguardando aprovação")
        self.assertContains(response, "Aguardando aprovação da loja")
        self.assertContains(response, self.pizza.nome)

    def test_acompanhamento_pendente_sem_link_de_recibo(self):
        pedido = self._pedido()

        response = self.client.get(
            reverse("acompanhar_pedido", kwargs={"token": pedido.token})
        )

        self.assertNotContains(response, "Ver recibo")
        self.assertNotContains(
            response, reverse("recibo", kwargs={"token": pedido.token})
        )

    def test_acompanhamento_aprovado_libera_link_de_recibo(self):
        pedido = self._pedido()
        alterar_status(pedido, Pedido.Status.APROVADO, usuario=self.usuario)

        response = self.client.get(
            reverse("acompanhar_pedido", kwargs={"token": pedido.token})
        )

        self.assertContains(response, "Ver recibo")
        self.assertContains(
            response, reverse("recibo", kwargs={"token": pedido.token})
        )
        self.assertNotContains(response, "Aguardando aprovação da loja")

    def test_acompanhamento_libera_recibo_em_todos_os_status_operacionais(self):
        pedido = self._pedido()
        for status in (
            Pedido.Status.APROVADO,
            Pedido.Status.PREPARANDO,
            Pedido.Status.SAIU,
            Pedido.Status.ENTREGUE,
        ):
            pedido = alterar_status(pedido, status)
            response = self.client.get(
                reverse("acompanhar_pedido", kwargs={"token": pedido.token})
            )

            self.assertContains(response, "Ver recibo", msg_prefix=status)

    def test_timeline_marca_etapa_atual(self):
        pedido = self._pedido()
        alterar_status(pedido, Pedido.Status.APROVADO)
        alterar_status(pedido, Pedido.Status.PREPARANDO)

        response = self.client.get(
            reverse("acompanhar_pedido", kwargs={"token": pedido.token})
        )

        self.assertContains(response, "timeline__etapa--atual")
        self.assertContains(response, "Em preparo")
        self.assertContains(response, "Aprovado pela loja")

    def test_acompanhamento_cancelado_mostra_motivo(self):
        pedido = self._pedido()
        alterar_status(
            pedido,
            Pedido.Status.CANCELADO,
            usuario=self.usuario,
            motivo="Endereço fora da área",
        )

        response = self.client.get(
            reverse("acompanhar_pedido", kwargs={"token": pedido.token})
        )

        self.assertContains(response, "cancelado")
        self.assertContains(response, "Endereço fora da área")
        self.assertNotContains(response, "Ver recibo")

    def test_acompanhamento_mostra_endereco_e_condominio(self):
        pedido = self._pedido(
            condominio=self.condominio, endereco=ENDERECO_COMPLETO
        )

        response = self.client.get(
            reverse("acompanhar_pedido", kwargs={"token": pedido.token})
        )

        self.assertContains(response, ENDERECO_COMPLETO)
        self.assertContains(response, self.condominio.nome)

    def test_acompanhamento_token_invalido_da_404(self):
        response = self.client.get(
            reverse(
                "acompanhar_pedido",
                kwargs={"token": "00000000-0000-0000-0000-000000000000"},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_acompanhamento_tem_cabecalhos_de_privacidade(self):
        pedido = self._pedido()

        response = self.client.get(
            reverse("acompanhar_pedido", kwargs={"token": pedido.token})
        )

        self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertIn("nofollow", response["X-Robots-Tag"])
        self.assertTrue(response.has_header("Cache-Control"))
        self.assertContains(
            response, '<meta name="robots" content="noindex, nofollow">'
        )
