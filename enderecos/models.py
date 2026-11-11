from django.db import models


class Condominio(models.Model):
    nome = models.CharField(max_length=120)
    endereco = models.CharField(max_length=150)
    numero = models.CharField(max_length=20, blank=True)
    bairro = models.CharField(max_length=80)
    cidade = models.CharField(max_length=80)
    cep = models.CharField(max_length=9, blank=True)
    referencia = models.CharField(max_length=150, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def endereco_completo(self):
        principal = self.endereco
        if self.numero:
            principal = f"{principal}, {self.numero}"

        partes = [principal]
        if self.bairro:
            partes.append(self.bairro)
        if self.cidade:
            partes.append(self.cidade)
        if self.cep:
            partes.append(f"CEP {self.cep}")
        return " - ".join(partes)
