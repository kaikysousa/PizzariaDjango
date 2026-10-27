import json
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from pedidos.models import Categoria, Pedido, Produto
from pedidos.services import criar_pedido


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.margherita = Produto.objects.create(
            nome="Margherita", preco="45.90", categoria=Categoria.PIZZA
        )
        self.coca = Produto.objects.create(
            nome="Coca-Cola", preco="12.00", categoria=Categoria.BEBIDA
        )
        self.dados = {
            "nome": "Ana",
            "telefone": "(11) 99999-9999",
            "endereco": "Rua A, 1",
            "endereco2": "Apto 2",
            "observacoes": "Sem cebola",
            "pagamento": "pix",
        }

    def _revisar(self, itens=None):
        itens = itens or [{"ids": [self.margherita.id], "quantidade": 2}]
        return self.client.post(
            reverse("revisar_pedido"),
            {"carrinho": json.dumps({"itens": itens})},
        )

    def _checkout_token(self):
        self.client.get(reverse("checkout"))
        return self.client.session["checkout_token"]

    def test_revisar_exige_post(self):
        response = self.client.get(reverse("revisar_pedido"))
        self.assertEqual(response.status_code, 405)

    def test_revisar_guarda_carrinho_na_sessao(self):
        response = self._revisar()
        self.assertRedirects(response, reverse("checkout"))
        self.assertEqual(
            self.client.session["carrinho"],
            [{"ids": [self.margherita.id], "quantidade": 2}],
        )

    def test_revisar_rejeita_json_invalido(self):
        response = self.client.post(
            reverse("revisar_pedido"), {"carrinho": "{invalido"}
        )
        self.assertRedirects(response, reverse("index"))
        self.assertNotIn("carrinho", self.client.session)

    def test_revisar_rejeita_carrinho_vazio(self):
        response = self.client.post(
            reverse("revisar_pedido"), {"carrinho": json.dumps({"itens": []})}
        )
        self.assertRedirects(response, reverse("index"))

    def test_checkout_sem_carrinho_redireciona(self):
        response = self.client.get(reverse("checkout"))
        self.assertRedirects(response, reverse("index"))

    def test_checkout_exibe_resumo(self):
        self._revisar()
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Margherita")
        self.assertContains(response, "91,80")

    def test_post_sem_csrf_e_rejeitado(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("revisar_pedido"),
            {
                "carrinho": json.dumps(
                    {"itens": [{"ids": [self.margherita.id], "quantidade": 1}]}
                )
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_cria_pedido_e_redireciona_para_recibo(self):
        self._revisar()
        dados = dict(self.dados, checkout_token=self._checkout_token())
        response = self.client.post(reverse("checkout"), dados)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Pedido.objects.count(), 1)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.total, Decimal("91.80"))
        self.assertEqual(pedido.telefone, "11999999999")
        self.assertNotIn("carrinho", self.client.session)
        self.assertRedirects(
            response, reverse("recibo", kwargs={"token": pedido.token})
        )

    def test_form_invalido_nao_cria_pedido(self):
        self._revisar()
        dados = dict(
            self.dados,
            nome="",
            checkout_token=self._checkout_token(),
        )
        response = self.client.post(reverse("checkout"), dados)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(response, "Este campo é obrigatório.")

    def test_total_adulterado_no_post_e_ignorado(self):
        self._revisar()
        dados = dict(
            self.dados,
            total="0.01",
            checkout_token=self._checkout_token(),
        )
        self.client.post(reverse("checkout"), dados)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.total, Decimal("91.80"))

    def test_recibo_por_token(self):
        pedido = criar_pedido(
            itens=[{"ids": [self.margherita.id], "quantidade": 1}],
            nome="Ana",
            telefone="11999999999",
            endereco="Rua A, 1",
        )
        response = self.client.get(
            reverse("recibo", kwargs={"token": pedido.token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Pedido #{pedido.id}")
        self.assertContains(response, "Margherita")

    def test_recibo_com_token_errado_da_404(self):
        response = self.client.get(
            reverse(
                "recibo",
                kwargs={"token": "00000000-0000-0000-0000-000000000000"},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_recibo_nao_limpa_carrinho_automaticamente(self):
        pedido = criar_pedido(
            itens=[{"ids": [self.margherita.id], "quantidade": 1}],
            nome="Ana",
            telefone="11999999999",
            endereco="Rua A, 1",
        )
        response = self.client.get(
            reverse("recibo", kwargs={"token": pedido.token})
        )
        conteudo = response.content.decode()
        self.assertNotIn("localStorage.clear", conteudo)
        self.assertIn("@page", self._css_recibo())
        self.assertIn("80mm", self._css_recibo())

    def test_payload_nao_objeto_nao_quebra(self):
        for payload in ("[]", "null", '"abc"', "123", "true"):
            response = self.client.post(
                reverse("revisar_pedido"), {"carrinho": payload}
            )
            self.assertRedirects(response, reverse("index"))

    def test_segundo_post_nao_duplica_pedido(self):
        self._revisar()
        dados = dict(self.dados, checkout_token=self._checkout_token())
        primeira = self.client.post(reverse("checkout"), dados)
        segunda = self.client.post(reverse("checkout"), dados)
        self.assertEqual(primeira.status_code, 302)
        self.assertEqual(segunda.status_code, 302)
        self.assertEqual(Pedido.objects.count(), 1)

    def test_mensagem_de_carrinho_vazio_aparece(self):
        response = self.client.get(reverse("checkout"), follow=True)
        self.assertContains(response, "Seu carrinho está vazio")

    def test_recibo_tem_cabecalhos_de_privacidade(self):
        pedido = criar_pedido(
            itens=[{"ids": [self.margherita.id], "quantidade": 1}],
            nome="Ana",
            telefone="11999999999",
            endereco="Rua A, 1",
        )
        response = self.client.get(
            reverse("recibo", kwargs={"token": pedido.token})
        )
        self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertTrue(response.has_header("Cache-Control"))

    @staticmethod
    def _css_recibo():
        from pathlib import Path

        caminho = (
            Path(__file__).resolve().parents[2]
            / "static"
            / "css"
            / "recibo.css"
        )
        return caminho.read_text(encoding="utf-8") if caminho.exists() else ""
