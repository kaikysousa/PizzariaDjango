from django.db import models

# Create your models here.
class Produto(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=100)
    descricao = models.TextField()

class Pedido(models.Model):
    items = models.CharField(max_length=3000)
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=100)
    endereco2 = models.CharField(max_length=100)
    observacoes = models.TextField()
    total = models.DecimalField(max_digits=10, decimal_places=2)