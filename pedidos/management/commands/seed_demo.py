from django.core.management.base import BaseCommand

from pedidos.models import Categoria, Pedido, Produto
from pedidos.services import criar_pedido

PRODUTOS = [
    ("Margherita", "45.90", Categoria.PIZZA, "Molho, mussarela e manjericão"),
    ("Calabresa", "49.90", Categoria.PIZZA, "Calabresa e cebola"),
    ("Quatro Queijos", "52.90", Categoria.PIZZA, "Mussarela, provolone, parmesão e gorgonzola"),
    ("Chocolate", "39.90", Categoria.PIZZA_DOCE, "Chocolate ao leite"),
    ("Coca-Cola 2L", "12.00", Categoria.BEBIDA, "Refrigerante"),
    ("Água Mineral", "5.00", Categoria.BEBIDA, "500 ml"),
]


class Command(BaseCommand):
    help = "Cria produtos e um pedido de demonstração; imprime o token do recibo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Recria o pedido de demonstração.",
        )

    def handle(self, *args, **options):
        for nome, preco, categoria, descricao in PRODUTOS:
            Produto.objects.update_or_create(
                nome=nome,
                defaults={
                    "preco": preco,
                    "categoria": categoria,
                    "descricao": descricao,
                },
            )

        if options["reset"]:
            Pedido.objects.all().delete()

        pedido = Pedido.objects.first()
        if pedido is None:
            margherita = Produto.objects.get(nome="Margherita")
            calabresa = Produto.objects.get(nome="Calabresa")
            coca = Produto.objects.get(nome="Coca-Cola 2L")
            pedido = criar_pedido(
                itens=[
                    {"ids": [margherita.id, calabresa.id], "quantidade": 1},
                    {"ids": [coca.id], "quantidade": 2},
                ],
                nome="Cliente Demonstração",
                telefone="11999999999",
                endereco="Rua das Pizzas, 100",
                endereco2="Apto 12",
                observacoes="Sem cebola",
                pagamento="pix",
            )

        self.stdout.write(f"SEED_DEMO_TOKEN={pedido.token}")
