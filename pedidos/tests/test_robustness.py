import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib import admin
from django.core.management import call_command
from django.test import TestCase, override_settings

from importar_produtos import importar
from pedidos.admin import PedidoAdmin, ProdutoAdmin
from pedidos.models import Categoria, ItemPedido, Pedido, Produto
from pedidos.services import criar_pedido


class RobustnessTests(TestCase):
    def setUp(self):
        self.produto = Produto.objects.create(
            nome="Margherita", preco="45.90", categoria=Categoria.PIZZA
        )

    def _csv(self, linhas):
        arquivo = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        escritor = csv.writer(arquivo)
        escritor.writerow(["nome", "preco", "categoria", "descricao"])
        escritor.writerows(linhas)
        arquivo.close()
        return arquivo.name

    def test_importar_csv(self):
        caminho = self._csv([["Calabresa", "49,90", "pizza", "Cebola"]])
        total = importar(caminho)
        self.assertEqual(total, 1)
        self.assertTrue(Produto.objects.filter(nome="Calabresa").exists())
        Path(caminho).unlink()

    def test_dry_run_nao_grava(self):
        caminho = self._csv([["Portuguesa", "55,00", "pizza", ""]])
        total = importar(caminho, dry_run=True)
        self.assertEqual(total, 1)
        self.assertFalse(Produto.objects.filter(nome="Portuguesa").exists())
        Path(caminho).unlink()

    def test_importar_valida_colunas(self):
        caminho = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        caminho.write("nome,preco\nX,1\n")
        caminho.close()
        with self.assertRaises(ValueError):
            importar(caminho.name)
        Path(caminho.name).unlink()

    @override_settings(DEBUG=True)
    def test_media_route_configurada(self):
        from django.conf import settings
        from django.conf.urls.static import static

        patterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        self.assertEqual(len(patterns), 1)
        texto = (Path(__file__).resolve().parents[2] / "DjangoProject" / "urls.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("MEDIA_URL", texto)

    def test_admin_configurado(self):
        self.assertIn(Produto, admin.site._registry)
        self.assertIn(Pedido, admin.site._registry)
        self.assertIn("total", PedidoAdmin.list_display)
        self.assertIn("categoria", ProdutoAdmin.list_filter)

    def test_str_dos_modelos(self):
        pedido = criar_pedido(
            itens=[{"ids": [self.produto.id], "quantidade": 1}],
            nome="Ana",
            telefone="11999999999",
            endereco="Rua A, 1",
        )
        item = pedido.itens.get()
        self.assertEqual(str(self.produto), "Margherita")
        self.assertIn("Ana", str(pedido))
        self.assertIn("Margherita", str(item))
        self.assertIsInstance(item, ItemPedido)

    def test_recibo_longo_renderiza_todos_os_itens(self):
        itens = [{"ids": [self.produto.id], "quantidade": 3} for _ in range(12)]
        pedido = criar_pedido(
            itens=itens,
            nome="Cliente Longo",
            telefone="11999999999",
            endereco="Rua A, 1",
        )
        response = self.client.get(f"/pedido/{pedido.token}/recibo/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Margherita", count=12)

    def test_seed_demo_cria_pedido(self):
        saida = StringIO()
        call_command("seed_demo", stdout=saida)
        self.assertIn("SEED_DEMO_TOKEN=", saida.getvalue())
        self.assertTrue(Pedido.objects.exists())

    def test_produto_indisponivel_some_do_cardapio(self):
        self.produto.disponivel = False
        self.produto.save(update_fields=["disponivel"])
        response = self.client.get("/")
        self.assertNotContains(response, "Margherita")

    def test_sessao_com_carrinho_corrompido_redireciona(self):
        sessao = self.client.session
        sessao["carrinho"] = [{"ids": [9999], "quantidade": 1}]
        sessao.save()
        response = self.client.get("/checkout/")
        self.assertRedirects(response, "/")
        self.assertNotIn("carrinho", self.client.session)

