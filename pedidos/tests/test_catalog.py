from django.test import TestCase
from django.urls import reverse

from pedidos.models import Categoria, Produto


class CatalogTests(TestCase):
    def setUp(self):
        self.produtos = []
        for indice in range(5):
            self.produtos.append(
                Produto.objects.create(
                    nome=f"Pizza {indice}",
                    preco="40.00",
                    categoria=Categoria.PIZZA if indice < 4 else Categoria.BEBIDA,
                )
            )

    def test_cardapio_mostra_todos_os_produtos(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(len(response.context["produtos"]), 5)
        self.assertNotIn("page_obj", response.context)
        self.assertContains(response, "Pizza 4")

    def test_preco_no_html_nao_e_localizado(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, 'data-preco="40.00"')
        self.assertNotContains(response, 'data-preco="40,00"')

    def test_agrupa_por_categoria_na_ordem_do_modelo(self):
        response = self.client.get(reverse("index"))
        grupos = response.context["grupos"]
        self.assertEqual(
            [grupo["valor"] for grupo in grupos], ["pizza", "bebida"]
        )
        self.assertEqual(len(grupos[0]["produtos"]), 4)
        self.assertEqual(len(grupos[1]["produtos"]), 1)

    def test_categoria_sem_produto_nao_rende_secao(self):
        response = self.client.get(reverse("index"), {"categoria": "pizza"})
        self.assertEqual(
            [grupo["valor"] for grupo in response.context["grupos"]], ["pizza"]
        )
        self.assertNotContains(response, 'id="grupo-bebida"')

    def test_filtro_por_categoria(self):
        response = self.client.get(reverse("index"), {"categoria": "bebida"})
        self.assertEqual(len(response.context["produtos"]), 1)
        self.assertEqual(response.context["produtos"][0].nome, "Pizza 4")

    def test_busca_por_nome(self):
        response = self.client.get(reverse("index"), {"q": "Pizza 3"})
        self.assertEqual(len(response.context["produtos"]), 1)

    def test_parametro_page_e_ignorado(self):
        for indice in range(6):
            Produto.objects.create(
                nome=f"Bebida {indice}", preco="5.00", categoria=Categoria.BEBIDA
            )
        response = self.client.get(
            reverse("index"), {"categoria": "bebida", "page": 2}
        )
        self.assertEqual(len(response.context["produtos"]), 7)
        self.assertTrue(
            all(
                produto.categoria == Categoria.BEBIDA
                for produto in response.context["produtos"]
            )
        )

    def test_busca_e_filtro_combinados(self):
        response = self.client.get(
            reverse("index"), {"q": "Pizza", "categoria": "pizza"}
        )
        self.assertEqual(len(response.context["produtos"]), 4)

    def test_ordenacao_estavel(self):
        response = self.client.get(reverse("index"), {"categoria": "pizza"})
        nomes = [produto.nome for produto in response.context["produtos"]]
        self.assertEqual(nomes, sorted(nomes))
