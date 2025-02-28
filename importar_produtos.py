import csv
from pedidos.models import Produto

with open('/home/kaiky/PycharmProjects/DjangoProject/cardapio.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        Produto.objects.create(
            nome=row['nome'],
            preco=row['preco'],
            categoria=row['categoria'],
            descricao=row['descricao']
        )
q