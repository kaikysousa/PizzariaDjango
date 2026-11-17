import io
import tempfile
import zipfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from enderecos.coleta import (
    chave_dedup,
    escrever_csv,
    formatar_cep,
    nome_para_exibicao,
    valor_revisado,
)
from enderecos.coleta_cnpj import (
    _competencias_de_xml,
    baixar_arquivo,
    ler_municipio,
    processar_parte,
)
from enderecos.coleta_merge import mesclar, separar_pendencias
from enderecos.coleta_osm import extrair_condominios
from enderecos.models import Condominio


class NormalizacaoTests(SimpleTestCase):
    def test_nome_para_exibicao_limpa_prefixo_e_bloco(self):
        self.assertEqual(
            nome_para_exibicao("", "CONDOMINIO DO EDIFICIO AVENCA BLOCO 7"),
            "Edifício Avenca",
        )

    def test_nome_para_exibicao_prefere_fantasia(self):
        self.assertEqual(
            nome_para_exibicao("Bella Vitta", "BELLA VITTA CLUB RESIDENCE I"),
            "Bella Vitta",
        )

    def test_colinas_1_e_2_ficam_distintos(self):
        self.assertNotEqual(
            chave_dedup("Colinas 1", "Rua A", "1", "Centro"),
            chave_dedup("Colinas 2", "Rua A", "1", "Centro"),
        )

    def test_chave_ignora_acento_caixa_e_espacos(self):
        self.assertEqual(
            chave_dedup("Residencial São José", "Rua A", "10", "Centro"),
            chave_dedup("residencial sao jose", "RUA A", "10", "centro"),
        )

    def test_formatar_cep(self):
        self.assertEqual(formatar_cep("72870000"), "72870-000")

    def test_valor_revisado_aceita_sim_e_um(self):
        self.assertTrue(valor_revisado("sim"))
        self.assertTrue(valor_revisado("1"))
        self.assertFalse(valor_revisado("nao"))


class CnpjTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _zip(self, nome, conteudo):
        caminho = self.dir / nome
        with zipfile.ZipFile(caminho, "w") as arquivo:
            arquivo.writestr(nome.replace(".zip", ".csv"), conteudo)
        return caminho

    def _estab(
        self,
        base,
        nome,
        situacao="02",
        cnae="8112500",
        uf="GO",
        municipio="9357",
        tipo="RUA",
        logradouro="DAS FLORES",
    ):
        campos = [""] * 30
        campos[0] = base
        campos[1] = "0001"
        campos[2] = "00"
        campos[3] = "1"
        campos[4] = nome
        campos[5] = situacao
        campos[11] = cnae
        campos[13] = tipo
        campos[14] = logradouro
        campos[15] = "10"
        campos[17] = "CENTRO"
        campos[18] = "72870000"
        campos[19] = uf
        campos[20] = municipio
        return ";".join(campos)

    def test_processa_somente_ativo_do_municipio_e_cnae(self):
        empresas = self._zip(
            "Empresas0.zip",
            "00000001;CONDOMINIO RESIDENCIAL TESTE\n"
            "00000002;INATIVO\n"
            "00000003;OUTRA CIDADE\n"
            "00000004;OUTRO CNAE\n",
        )
        estabelecimentos = self._zip(
            "Estabelecimentos0.zip",
            "\n".join(
                [
                    self._estab("00000001", "CONDOMINIO TESTE"),
                    self._estab("00000002", "INATIVO", situacao="08"),
                    self._estab(
                        "00000003", "OUTRA CIDADE", municipio="9358"
                    ),
                    self._estab("00000004", "OUTRO CNAE", cnae="6821801"),
                ]
            )
            + "\n",
        )

        linhas = processar_parte(
            empresas, estabelecimentos, "9357", "GO", "8112500"
        )

        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["nome"], "Condomínio Teste")
        self.assertEqual(linhas[0]["endereco"], "Rua das Flores")
        self.assertEqual(linhas[0]["bairro"], "Centro")
        self.assertEqual(linhas[0]["cep"], "72870-000")
        self.assertEqual(linhas[0]["fonte"], "cnpj")
        self.assertEqual(linhas[0]["revisado"], "nao")
        self.assertEqual(linhas[0]["ativo"], "sim")
        self.assertEqual(linhas[0]["nome_origem"], "CONDOMINIO RESIDENCIAL TESTE")

    def test_ler_municipio_devolve_codigo(self):
        caminho = self._zip(
            "Municipios.zip", "9357;VALPARAISO DE GOIAS\n"
        )

        self.assertEqual(
            ler_municipio(caminho, "Valparaíso de Goiás"), "9357"
        )

    def test_nao_duplica_tipo_do_logradouro(self):
        empresas = self._zip(
            "Empresas0.zip",
            "00000001;CONDOMINIO RESIDENCIAL TESTE\n",
        )
        estabelecimentos = self._zip(
            "Estabelecimentos0.zip",
            self._estab(
                "00000001",
                "CONDOMINIO TESTE",
                logradouro="RUA DAS FLORES",
            )
            + "\n",
        )

        linhas = processar_parte(
            empresas, estabelecimentos, "9357", "GO", "8112500"
        )

        self.assertEqual(linhas[0]["endereco"], "Rua das Flores")


class CsvComNulTests(SimpleTestCase):
    def test_nul_nao_quebra_a_leitura(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)

            def criar(nome, conteudo):
                caminho = pasta / nome
                with zipfile.ZipFile(caminho, "w") as arquivo:
                    arquivo.writestr(
                        nome.replace(".zip", ".csv"), conteudo
                    )
                return caminho

            empresas = criar(
                "Empresas0.zip",
                "00000001;CONDOMINIO RESIDENCIAL TESTE\n",
            )
            campos = [""] * 30
            campos[0] = "00000001"
            campos[1] = "0001"
            campos[2] = "00"
            campos[3] = "1"
            campos[4] = "CONDOMINIO TESTE"
            campos[5] = "02"
            campos[11] = "8112500"
            campos[13] = "RUA"
            campos[14] = "DAS FLORES"
            campos[15] = "10"
            campos[16] = "BLOCO\x00A"
            campos[17] = "CENTRO"
            campos[18] = "72870000"
            campos[19] = "GO"
            campos[20] = "1066"
            estabelecimentos = criar(
                "Estabelecimentos0.zip", ";".join(campos) + "\n"
            )

            linhas = processar_parte(
                empresas,
                estabelecimentos,
                "1066",
                "GO",
                "8112500",
            )

            self.assertEqual(len(linhas), 1)
            self.assertNotIn("\x00", linhas[0]["referencia"])
            self.assertIn("Bloco", linhas[0]["referencia"])


class CompetenciaTests(SimpleTestCase):
    def test_extrai_competencias_do_propfind(self):
        conteudo = b"""<?xml version="1.0"?>
        <d:multistatus xmlns:d="DAV:">
          <d:response><d:href>/public.php/dav/files/TOKEN/2026-10/</d:href></d:response>
          <d:response><d:href>/public.php/dav/files/TOKEN/2026-11/</d:href></d:response>
          <d:response><d:href>/public.php/dav/files/TOKEN/cnpj.tar.gz</d:href></d:response>
        </d:multistatus>"""

        self.assertEqual(
            _competencias_de_xml(conteudo), ["2026-10", "2026-11"]
        )


class _RespostaFalsa:
    def __init__(self, conteudo, content_length=None):
        self._arquivo = io.BytesIO(conteudo)
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, tamanho=-1):
        return self._arquivo.read(tamanho)


class DownloadTests(SimpleTestCase):
    def _baixar(self, resposta):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch(
                "enderecos.coleta_cnpj.urllib.request.urlopen",
                return_value=resposta,
            ):
                with self.assertRaises(RuntimeError):
                    baixar_arquivo(
                        "Empresas0.zip",
                        Path(tmp),
                        log=lambda *_: None,
                        tentativas=1,
                        url_base="https://exemplo.invalido/",
                    )
            self.assertFalse((Path(tmp) / "Empresas0.zip").exists())

    def test_rejeita_download_truncado(self):
        self._baixar(_RespostaFalsa(b"abc", content_length=10))

    def test_rejeita_download_vazio(self):
        self._baixar(_RespostaFalsa(b"", content_length=10))


class OsmTests(SimpleTestCase):
    def test_extrai_apenas_elementos_com_nome(self):
        dados = {
            "elements": [
                {
                    "type": "way",
                    "id": 123,
                    "center": {"lat": -16.05, "lon": -47.97},
                    "tags": {
                        "name": "Residencial Colinas 2",
                        "landuse": "residential",
                        "addr:street": "Rua das Palmeiras",
                        "addr:housenumber": "100",
                        "addr:suburb": "Ypiranga",
                        "addr:postcode": "72870000",
                    },
                },
                {
                    "type": "node",
                    "id": 456,
                    "tags": {"landuse": "residential"},
                },
            ]
        }

        linhas = extrair_condominios(dados, "Valparaíso de Goiás")

        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["nome"], "Residencial Colinas 2")
        self.assertEqual(linhas[0]["endereco"], "Rua das Palmeiras")
        self.assertEqual(linhas[0]["bairro"], "Ypiranga")
        self.assertEqual(linhas[0]["cep"], "72870-000")
        self.assertEqual(linhas[0]["fonte"], "osm")
        self.assertEqual(linhas[0]["revisado"], "nao")
        self.assertEqual(linhas[0]["referencia"], "osm:way/123")

    def test_nome_generico_e_ignorado(self):
        dados = {
            "elements": [
                {"type": "way", "id": 1, "tags": {"name": "Residencial"}},
                {"type": "way", "id": 2, "tags": {"name": "Condomínio"}},
            ]
        }

        self.assertEqual(
            extrair_condominios(dados, "Valparaíso de Goiás"), []
        )

    def test_descarta_comercio_sem_endereco_completo(self):
        dados = {
            "elements": [
                {
                    "type": "node",
                    "id": 3,
                    "tags": {
                        "name": "Nillmart Supermercados - Jardim Oriente",
                        "shop": "supermarket",
                        "addr:street": "Rua Capitão da PM Carlos Silva",
                        "addr:suburb": "Jardim Oriente",
                    },
                }
            ]
        }

        self.assertEqual(
            extrair_condominios(dados, "Valparaíso de Goiás"), []
        )

    def test_descarta_quadra_sem_nome_de_condominio(self):
        dados = {
            "elements": [
                {
                    "type": "node",
                    "id": 6,
                    "tags": {"name": "Qc-02 Conjunto B"},
                }
            ]
        }

        self.assertEqual(
            extrair_condominios(dados, "Valparaíso de Goiás"), []
        )

    def test_mantem_condominio_sem_endereco(self):
        dados = {
            "elements": [
                {
                    "type": "way",
                    "id": 4,
                    "tags": {
                        "name": "Condomínio Residencial Flores do Bosque"
                    },
                }
            ]
        }

        self.assertEqual(
            len(extrair_condominios(dados, "Valparaíso de Goiás")), 1
        )

    def test_mantem_nome_comum_com_endereco_completo(self):
        dados = {
            "elements": [
                {
                    "type": "way",
                    "id": 5,
                    "tags": {
                        "name": "Jardim das Flores",
                        "addr:street": "Rua A",
                        "addr:suburb": "Centro",
                    },
                }
            ]
        }

        self.assertEqual(
            len(extrair_condominios(dados, "Valparaíso de Goiás")), 1
        )

    def test_cidade_usa_a_cidade_alvo(self):
        dados = {
            "elements": [
                {
                    "type": "way",
                    "id": 7,
                    "tags": {
                        "name": "Condomínio Teste",
                        "addr:city": "Brasília",
                    },
                }
            ]
        }

        linhas = extrair_condominios(dados, "Valparaíso de Goiás")

        self.assertEqual(linhas[0]["cidade"], "Valparaíso de Goiás")


BASE = {
    "nome": "Edifício Avenca",
    "endereco": "Rua A",
    "numero": "10",
    "bairro": "Centro",
    "cidade": "Valparaíso de Goiás",
    "cep": "72870-000",
    "referencia": "",
    "ativo": "sim",
    "revisado": "nao",
    "fonte": "cnpj",
    "nome_origem": "CONDOMINIO DO EDIFICIO AVENCA",
    "cnpj": "00.000.001/0001-00",
}


class MergeTests(SimpleTestCase):
    def test_cnpj_vence_osm_na_mesma_chave(self):
        cnpj = dict(BASE)
        osm = {**BASE, "fonte": "osm", "cep": "", "nome": "Avenca"}

        resultado = mesclar([cnpj, osm])

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["fonte"], "cnpj")

    def test_osm_sem_par_permanece(self):
        osm = {
            **BASE,
            "nome": "Residencial Colinas 2",
            "fonte": "osm",
            "cep": "",
            "cnpj": "",
        }

        resultado = mesclar([osm])

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["fonte"], "osm")

    def test_linha_sem_bairro_vai_para_pendencias(self):
        linha = {**BASE, "bairro": ""}

        validas, pendencias = separar_pendencias([linha])

        self.assertEqual(validas, [])
        self.assertEqual(len(pendencias), 1)


class ImportarCondominiosTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _csv(self, revisado="sim", bairro="Centro"):
        caminho = self.dir / "condominios.csv"
        caminho.write_text(
            "nome;endereco;numero;bairro;cidade;cep;referencia;ativo;"
            "revisado;fonte;nome_origem;cnpj\n"
            "Residencial Aurora;Rua A;10;"
            f"{bairro};Valparaíso de Goiás;72870-000;;sim;"
            f"{revisado};cnpj;RESIDENCIAL AURORA;00.000.001/0001-00\n",
            encoding="utf-8-sig",
        )
        return caminho

    def _rodar(self, caminho, *args):
        saida = StringIO()
        call_command(
            "importar_condominios", str(caminho), *args, stdout=saida
        )
        return saida.getvalue()

    def test_dry_run_nao_grava(self):
        caminho = self._csv()

        saida = self._rodar(caminho, "--dry-run")

        self.assertEqual(Condominio.objects.count(), 0)
        self.assertIn("criados=1", saida)

    def test_importa_linha_revisada(self):
        caminho = self._csv()

        saida = self._rodar(caminho)

        self.assertEqual(Condominio.objects.count(), 1)
        self.assertIn("criados=1", saida)
        condominio = Condominio.objects.get()
        self.assertEqual(condominio.nome, "Residencial Aurora")
        self.assertEqual(condominio.bairro, "Centro")
        self.assertEqual(condominio.cep, "72870-000")

    def test_ignora_nao_revisada(self):
        caminho = self._csv(revisado="nao")

        saida = self._rodar(caminho)

        self.assertEqual(Condominio.objects.count(), 0)
        self.assertIn("ignorados=1", saida)

    def test_linha_sem_bairro_vira_pendencia(self):
        caminho = self._csv(bairro="")

        saida = self._rodar(caminho)

        self.assertEqual(Condominio.objects.count(), 0)
        self.assertIn("pendencias=1", saida)

    def test_rodar_duas_vezes_nao_duplica(self):
        caminho = self._csv()

        self._rodar(caminho)
        saida = self._rodar(caminho)

        self.assertEqual(Condominio.objects.count(), 1)
        self.assertIn("existentes=1", saida)

    def test_nao_sobrescreve_cadastro_manual(self):
        Condominio.objects.create(
            nome="Residencial Aurora",
            endereco="Rua A",
            numero="10",
            bairro="Centro",
            cidade="Valparaíso de Goiás",
            referencia="manual",
        )
        caminho = self._csv()

        self._rodar(caminho)

        self.assertEqual(Condominio.objects.count(), 1)
        self.assertEqual(Condominio.objects.get().referencia, "manual")

    def test_incluir_nao_revisados(self):
        caminho = self._csv(revisado="nao")

        self._rodar(caminho, "--incluir-nao-revisados")

        self.assertEqual(Condominio.objects.count(), 1)


class FluxoCompletoTests(TestCase):
    def test_do_zip_do_cnpj_ao_banco(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)

            def criar_zip(nome, conteudo):
                caminho = pasta / nome
                with zipfile.ZipFile(caminho, "w") as arquivo:
                    arquivo.writestr(
                        nome.replace(".zip", ".csv"), conteudo
                    )
                return caminho

            municipios = criar_zip(
                "Municipios.zip", "9357;VALPARAISO DE GOIAS\n"
            )
            empresas = criar_zip(
                "Empresas0.zip",
                "00000001;CONDOMINIO RESIDENCIAL TESTE\n",
            )

            campos = [""] * 30
            campos[0] = "00000001"
            campos[1] = "0001"
            campos[2] = "00"
            campos[3] = "1"
            campos[4] = "CONDOMINIO TESTE"
            campos[5] = "02"
            campos[11] = "8112500"
            campos[13] = "RUA"
            campos[14] = "DAS FLORES"
            campos[15] = "10"
            campos[17] = "CENTRO"
            campos[18] = "72870000"
            campos[19] = "GO"
            campos[20] = "9357"
            estabelecimentos = criar_zip(
                "Estabelecimentos0.zip", ";".join(campos) + "\n"
            )

            codigo = ler_municipio(municipios, "Valparaíso de Goiás")
            linhas = processar_parte(
                empresas,
                estabelecimentos,
                codigo,
                "GO",
                "8112500",
            )
            for linha in linhas:
                linha["revisado"] = "sim"
            caminho_csv = pasta / "condominios.csv"
            escrever_csv(linhas, caminho_csv)

            call_command(
                "importar_condominios", str(caminho_csv), stdout=StringIO()
            )

            self.assertTrue(
                Condominio.objects.filter(nome="Condomínio Teste").exists()
            )
            condominio = Condominio.objects.get()
            self.assertEqual(condominio.bairro, "Centro")
            self.assertEqual(condominio.cep, "72870-000")
