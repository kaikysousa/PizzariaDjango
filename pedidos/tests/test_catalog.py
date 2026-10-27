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

    def test_primeira_pagina_tem_quatro_produtos(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(len(response.context["produtos"]), 4)
        self.assertTrue(response.context["page_obj"].has_next())

    def test_segunda_pagina_tem_o_restante(self):
        response = self.client.get(reverse("index"), {"page": 2})
        self.assertEqual(len(response.context["produtos"]), 1)
        self.assertFalse(response.context["page_obj"].has_next())

    def test_filtro_por_categoria(self):
        response = self.client.get(reverse("index"), {"categoria": "bebida"})
        self.assertEqual(len(response.context["produtos"]), 1)
        self.assertEqual(response.context["produtos"][0].nome, "Pizza 4")

    def test_busca_por_nome(self):
        response = self.client.get(reverse("index"), {"q": "Pizza 3"})
        self.assertEqual(len(response.context["produtos"]), 1)

    def test_filtro_sobrevive_a_paginacao(self):
        for indice in range(6):
            Produto.objects.create(
                nome=f"Bebida {indice}", preco="5.00", categoria=Categoria.BEBIDA
            )
        response = self.client.get(
            reverse("index"), {"categoria": "bebida", "page": 2}
        )
        self.assertContains(response, "categoria=bebida")

    def test_busca_e_filtro_combinados(self):
        response = self.client.get(
            reverse("index"), {"q": "Pizza", "categoria": "pizza"}
        )
        self.assertEqual(len(response.context["produtos"]), 4)

    def test_ordenacao_estavel(self):
        response = self.client.get(reverse("index"), {"categoria": "pizza"})
        nomes = [produto.nome for produto in response.context["produtos"]]
        self.assertEqual(nomes, sorted(nomes))
