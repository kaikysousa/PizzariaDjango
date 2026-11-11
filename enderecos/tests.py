from django.test import TestCase

from enderecos.models import Condominio


class CondominioTests(TestCase):
    def test_cria_condominio_com_endereco_completo(self):
        condominio = Condominio.objects.create(
            nome="Residencial Aurora",
            endereco="Rua das Flores",
            numero="123",
            bairro="Centro",
            cidade="São Paulo",
            cep="01001-000",
        )

        self.assertEqual(str(condominio), "Residencial Aurora")
        self.assertTrue(condominio.ativo)
        self.assertEqual(
            condominio.endereco_completo,
            "Rua das Flores, 123 - Centro - São Paulo - CEP 01001-000",
        )

    def test_endereco_completo_sem_numero_e_sem_cep(self):
        condominio = Condominio.objects.create(
            nome="Condomínio Sem Número",
            endereco="Avenida Central",
            bairro="Jardins",
            cidade="Recife",
        )

        self.assertEqual(
            condominio.endereco_completo,
            "Avenida Central - Jardins - Recife",
        )

    def test_ordering_por_nome(self):
        Condominio.objects.create(
            nome="Zeta",
            endereco="Rua Z",
            bairro="Bairro",
            cidade="Cidade",
        )
        Condominio.objects.create(
            nome="Alfa",
            endereco="Rua A",
            bairro="Bairro",
            cidade="Cidade",
        )

        self.assertEqual(
            list(Condominio.objects.values_list("nome", flat=True)),
            ["Alfa", "Zeta"],
        )
