# Coleta de condomínios de Valparaíso de Goiás — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Coletar condomínios residenciais de Valparaíso de Goiás a partir do CNPJ oficial e do OSM, gerar um CSV revisável e importar só as linhas aprovadas, sem sobrescrever cadastro manual.

**Architecture:** Um módulo de normalização compartilhado (`enderecos/coleta.py`), coletores isolados por fonte (`coleta_cnpj.py`, `coleta_osm.py`), merge/dedup com procedência (`coleta_merge.py`), um CLI local (`scripts/coletar_condominios.py`) e um management command create-only (`importar_condominios`). Nenhuma dependência nova; tudo com biblioteca padrão.

**Tech Stack:** Python 3.12, Django 5.2, `zipfile`/`csv`/`urllib`/`argparse`, testes com `django.test`.

**Spec:** `docs/superpowers/specs/2026-11-17-coleta-condominios-design.md`

## Global Constraints

- Sem dependências novas: só biblioteca padrão.
- CSV de revisão: delimitador `;`, codificação `utf-8-sig`, colunas
  `nome;endereco;numero;bairro;cidade;cep;referencia;ativo;revisado;fonte;nome_origem;cnpj`.
- `revisado` só entra na importação quando for `sim`.
- Importação create-only: nunca atualiza nem apaga `Condominio`.
- Google Maps não é usado por código; só conferência humana.
- Nada de rodar o coletor na VM de produção.
- Todo código novo passa em `python -m ruff check .` e na suíte completa.
- Os arquivos da Receita usam Latin-1, delimitador `;`, campos entre aspas.
- O download completo do CNPJ tem vários GB; o script processa parte por parte.

## Review Focus

- Nome com bloco/torre deve colapsar sem perder `Colinas 1` × `Colinas 2`.
- Linha sem bairro/cidade não pode entrar no banco nem sumir sem relatório.
- CNPJ de outro município, inativo ou de outro CNAE não pode vazar para o CSV.
- Importação repetida não pode duplicar nem sobrescrever registro manual.
- CSV com acentos precisa abrir corretamente no Excel pt-BR.

---

### Task 1: Normalização e schema do CSV

**Files:**
- Create: `enderecos/coleta.py`
- Test: `enderecos/test_coleta.py`

**Interfaces:**
- Produces:
  - `COLUNAS_CSV: tuple[str, ...]`
  - `normalizar_espacos(valor: str) -> str`
  - `sem_acento(valor: str) -> str`
  - `limpar_sufixo_bloco(nome: str) -> str`
  - `nome_para_exibicao(nome_fantasia: str, razao_social: str) -> str`
  - `chave_dedup(nome: str, endereco: str, numero: str, bairro: str) -> str`
  - `formatar_cep(cep: str) -> str`
  - `valor_revisado(valor: str) -> bool`
  - `capitalizar_texto(valor: str) -> str`
  - `escrever_csv(linhas: list[dict], caminho: Path) -> None`
  - `ler_csv(caminho: Path) -> list[dict]`

- [ ] **Step 1: Write the failing tests**

```python
from django.test import SimpleTestCase

from enderecos.coleta import (
    chave_dedup,
    formatar_cep,
    nome_para_exibicao,
    valor_revisado,
)


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test enderecos.test_coleta.NormalizacaoTests -v 2`
Expected: FAIL/ERROR because `enderecos.coleta` does not exist.

- [ ] **Step 3: Implement `enderecos/coleta.py`**

Regras:
- `limpar_sufixo_bloco` remove `BLOCO n`, `TORRE x`, `ENTRADA x` no fim do
  nome; não remove números de empreendimento.
- `nome_para_exibicao` remove prefixos `CONDOMINIO`, `CONDOMINIO DO`,
  `CONDOMINIO DO EDIFICIO`, `CONDOMINIO RESIDENCIAL`, `RESIDENCIAL`,
  `EDIFICIO`, `COND.`; troca `EDIFICIO` por `Edifício`; capitaliza palavras,
  preservando numerais romanos (`I`, `II`, `III`, `IV`) em maiúsculas.
- `chave_dedup` usa `sem_acento`, minúsculas, remove pontuação, aplica
  `limpar_sufixo_bloco` e junta nome + endereço + número + bairro.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test enderecos.test_coleta.NormalizacaoTests -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add enderecos/coleta.py enderecos/test_coleta.py
git commit -m "feat(coleta): normaliza nomes e chaves de condominios"
```

---

### Task 2: Coletor do CNPJ oficial

**Files:**
- Create: `enderecos/coleta_cnpj.py`
- Test: `enderecos/test_coleta.py`

**Interfaces:**
- Consumes: `COLUNAS_CSV`, `nome_para_exibicao`, `formatar_cep`.
- Produces:
  - `URL_BASE: str`
  - `ler_municipio(caminho_zip: Path, municipio: str) -> str`
  - `processar_parte(empresas_zip: Path, estabelecimentos_zip: Path, codigo_municipio: str, uf: str, cnae: str) -> list[dict[str, str]]`
  - `coletar_cnpj(cache_dir: Path, saida_csv: Path, uf: str, municipio: str, cnae: str, partes: range, log=print) -> list[dict[str, str]]`

Layout dos CSVs da Receita (Latin-1, `;`):
- Estabelecimentos: `0` CNPJ base, `1` ordem, `2` DV, `4` nome fantasia,
  `5` situação, `11` CNAE principal, `13` tipo logradouro, `14` logradouro,
  `15` número, `16` complemento, `17` bairro, `18` CEP, `19` UF,
  `20` município.
- Empresas: `0` CNPJ base, `1` razão social.
- Municípios: `0` código, `1` descrição.
- Situação ativa = `02`; CNAE = `8112500`.

- [ ] **Step 1: Write the failing test with fixture zips**

```python
import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

from enderecos.coleta_cnpj import ler_municipio, processar_parte


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

    def test_processa_somente_ativo_do_municipio_e_cnae(self):
        empresas = self._zip(
            "Empresas0.zip",
            "00000001;CONDOMINIO TESTE\n00000002;OUTRO\n",
        )
        estabelecimentos = self._zip(
            "Estabelecimentos0.zip",
            "\n".join(
                [
                    '00000001;0001;00;1;CONDOMINIO TESTE;02;;;'
                    ';2020-01-01;8112500;;RUA;DAS FLORES;10;;CENTRO;'
                    '72870000;GO;9357;;;',
                    '00000002;0001;00;1;OUTRO;02;;;'
                    ';2020-01-01;8112500;;RUA;B;20;;CENTRO;'
                    '72870000;GO;9357;;;',
                    '00000001;0001;00;1;INATIVO;08;;;'
                    ';2020-01-01;8112500;;RUA;C;30;;CENTRO;'
                    '72870000;GO;9357;;;',
                ]
            )
            + "\n",
        )

        linhas = processar_parte(empresas, estabelecimentos, "9357", "GO", "8112500")

        self.assertEqual(len(linhas), 2)
        self.assertEqual(linhas[0]["nome"], "Condomínio Teste")
        self.assertEqual(linhas[0]["fonte"], "cnpj")
        self.assertEqual(linhas[0]["revisado"], "nao")
        self.assertEqual(linhas[0]["endereco"], "Rua das Flores")
        self.assertEqual(linhas[0]["cep"], "72870-000")

    def test_ler_municipio_devolve_codigo(self):
        caminho = self._zip("Municipios.zip", "9357;VALPARAISO DE GOIAS\n")

        self.assertEqual(ler_municipio(caminho, "Valparaíso de Goiás"), "9357")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test enderecos.test_coleta.CnpjTests -v 2`
Expected: FAIL/ERROR because `enderecos.coleta_cnpj` does not exist.

- [ ] **Step 3: Implement `enderecos/coleta_cnpj.py`**

- `_ler_csv_zip` abre o primeiro `.csv` do zip com `encoding="latin-1"`,
  `delimiter=";"`, `quotechar='"'`.
- `baixar_arquivo(nome, cache_dir)` baixa de `URL_BASE + nome` com
  `urllib.request`, User-Agent próprio, e reaproveita o arquivo se existir.
- `coletar_cnpj` baixa `Municipios.zip`, `Cnaes.zip`, e para cada parte
  `Empresas{i}.zip` + `Estabelecimentos{i}.zip`; processa, acumula, escreve o
  CSV com `escrever_csv` (Task 4) e retorna as linhas.
- CNPJ formatado: `00000001/0001-00`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test enderecos.test_coleta.CnpjTests -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add enderecos/coleta_cnpj.py enderecos/test_coleta.py
git commit -m "feat(coleta): le e filtra a base aberta do CNPJ"
```

---

### Task 3: Coletor OSM

**Files:**
- Create: `enderecos/coleta_osm.py`
- Test: `enderecos/test_coleta.py`

**Interfaces:**
- Produces:
  - `BBOX_VALPARAISO: str` = `-16.12,-48.03,-16.01,-47.92`
  - `extrair_condominios(dados: dict, cidade: str) -> list[dict[str, str]]`
  - `consultar_overpass(bbox: str, timeout: int = 120, log=print) -> dict`
  - `coletar_osm(saida_csv: Path, bbox: str, cidade: str, log=print) -> list[dict[str, str]]`

- [ ] **Step 1: Write the failing test**

```python
class OsmTests(SimpleTestCase):
    def test_extrai_apenas_elementos_com_nome(self):
        dados = {
            "elements": [
                {
                    "type": "way",
                    "center": {"lat": -16.05, "lon": -47.97},
                    "tags": {
                        "name": "Residencial Colinas 2",
                        "landuse": "residential",
                        "addr:street": "Rua das Palmeiras",
                        "addr:housenumber": "100",
                        "addr:suburb": "Ypiranga",
                    },
                },
                {"type": "node", "tags": {"landuse": "residential"}},
            ]
        }

        linhas = extrair_condominios(dados, "Valparaíso de Goiás")

        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["nome"], "Residencial Colinas 2")
        self.assertEqual(linhas[0]["fonte"], "osm")
        self.assertEqual(linhas[0]["revisado"], "nao")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test enderecos.test_coleta.OsmTests -v 2`
Expected: FAIL/ERROR because `enderecos.coleta_osm` does not exist.

- [ ] **Step 3: Implement `enderecos/coleta_osm.py`**

- Consulta Overpass com `landuse=residential`, `building=residential` e nomes
  que casem `Residencial|Condom[ií]nio|Colinas|Jardim|Parque|Vila|Conjunto`.
- Endpoints em ordem: `overpass-api.de`, `overpass.kumi.systems`,
  `overpass.private.coffee`; 3 tentativas com pausa.
- `extrair_condominios` usa `tags.name`, `addr:street`, `addr:housenumber`,
  `addr:suburb`, `addr:postcode`; cidade padrão do argumento; `referencia` =
  `osm:{type}/{id}`.
- Nome genérico (`Residencial`, `Condomínio`) sem complemento é descartado.

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test enderecos.test_coleta.OsmTests -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add enderecos/coleta_osm.py enderecos/test_coleta.py
git commit -m "feat(coleta): consulta OSM e extrai condominios"
```

---

### Task 4: Merge, CSV de revisão e CLI

**Files:**
- Create: `enderecos/coleta_merge.py`
- Create: `scripts/coletar_condominios.py`
- Modify: `.gitignore`
- Test: `enderecos/test_coleta.py`

**Interfaces:**
- Consumes: `COLUNAS_CSV`, `chave_dedup`, `escrever_csv`, `ler_csv`.
- Produces:
  - `mesclar(linhas: list[dict[str, str]]) -> list[dict[str, str]]`
  - `separar_pendencias(linhas) -> tuple[list[dict], list[dict]]`

- [ ] **Step 1: Write the failing tests**

```python
class MergeTests(SimpleTestCase):
    def test_cnpj_vence_osm_na_mesma_chave(self):
        cnpj = {
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
        osm = {**cnpj, "fonte": "osm", "cep": "", "nome": "Avenca"}

        resultado = mesclar([cnpj, osm])

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["fonte"], "cnpj")

    def test_linha_sem_bairro_vai_para_pendencias(self):
        linha = {**BASE, "bairro": ""}

        validas, pendencias = separar_pendencias([linha])

        self.assertEqual(validas, [])
        self.assertEqual(len(pendencias), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test enderecos.test_coleta.MergeTests -v 2`
Expected: FAIL/ERROR because `enderecos.coleta_merge` does not exist.

- [ ] **Step 3: Implement merge e CLI**

- `escrever_csv`: `;`, `utf-8-sig`, `newline=""`, `csv.DictWriter`,
  `extrasaction="ignore"`.
- `mesclar`: agrupa por `chave_dedup`; ordem de precedência `cnpj` > `osm` >
  `prefeitura`; mantém a primeira linha da fonte vencedora; preserva
  `revisado=nao`.
- `separar_pendencias`: pendente se faltar `nome`, `endereco`, `bairro` ou
  `cidade`.
- CLI `scripts/coletar_condominios.py`:
  - `--fonte` (`cnpj`, `osm`, `tudo`), `--saida-dir` (default `dados`),
    `--cache-dir` (default `.cache-cnpj`), `--uf GO`,
    `--municipio "VALPARAISO DE GOIAS"`, `--cnae 8112500`,
    `--bbox`, `--partes` (default `0-9`).
  - `tudo`: roda CNPJ, roda OSM (falha do OSM não aborta; loga aviso),
    mescla, grava `dados/condominios.csv` e
    `dados/condominios-pendencias.csv`.
  - Imprime resumo: total, por fonte, duplicados, pendências.
- `.gitignore`: adicionar `dados/` e `.cache-cnpj/`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test enderecos.test_coleta.MergeTests -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add enderecos/coleta_merge.py scripts/coletar_condominios.py .gitignore enderecos/test_coleta.py
git commit -m "feat(coleta): mescla fontes e gera CSV de revisao"
```

---

### Task 5: Comando de importação

**Files:**
- Create: `enderecos/management/__init__.py`
- Create: `enderecos/management/commands/__init__.py`
- Create: `enderecos/management/commands/importar_condominios.py`
- Test: `enderecos/test_coleta.py`

**Interfaces:**
- Consumes: `ler_csv`, `chave_dedup`, `valor_revisado`.
- Produces: comando `importar_condominios <csv> [--dry-run] [--incluir-nao-revisados]`.

- [ ] **Step 1: Write the failing tests**

```python
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from enderecos.models import Condominio


class ImportarCondominiosTests(TestCase):
    def _csv(self, revisado="sim", bairro="Centro"):
        caminho = Path(self.tmp.name) / "condominios.csv"
        caminho.write_text(
            "nome;endereco;numero;bairro;cidade;cep;referencia;ativo;"
            "revisado;fonte;nome_origem;cnpj\n"
            f"Residencial Aurora;Rua A;10;{bairro};Valparaíso de Goiás;"
            f"72870-000;;sim;{revisado};cnpj;RESIDENCIAL AURORA;00.000.001/0001-00\n",
            encoding="utf-8-sig",
        )
        return caminho
```

Casos: dry-run não grava; importa `revisado=sim`; ignora `nao`; linha sem
bairro vira pendência; rodar duas vezes não duplica; registro manual
existente com a mesma chave não é sobrescrito.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test enderecos.test_coleta.ImportarCondominiosTests -v 2`
Expected: FAIL/ERROR because the command does not exist.

- [ ] **Step 3: Implement the command**

- `csv.DictReader` com `delimiter=";"`.
- `--dry-run` e `--incluir-nao-revisados`.
- Chave dos existentes calculada uma vez com `chave_dedup`.
- Contadores `criados`, `existentes`, `ignorados`, `pendencias`; saída
  `criados=N existentes=N ignorados=N pendencias=N`.
- `transaction.atomic` no bloco de criação.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test enderecos.test_coleta.ImportarCondominiosTests -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add enderecos/management enderecos/test_coleta.py
git commit -m "feat(enderecos): importa condominios de CSV revisado"
```

---

### Task 6: Documentação operacional e LAI

**Files:**
- Create: `docs/COLETA-CONDOMINIOS.md`
- Create: `docs/LAI-CONDOMINIOS-VALPARAISO.md`

Conteúdo mínimo:
- Passo a passo do coletor, tamanho/tempo do download, cache, revisão no
  Excel, `--dry-run`, backup antes da importação.
- Aviso sobre Google Maps e OSM.
- Texto do pedido de LAI à prefeitura, com base na Lei 12.527/2011, campos
  pedidos e formato CSV/planilha.

- [ ] **Step 1: Escrever os dois documentos**
- [ ] **Step 2: Revisar links e comandos**
- [ ] **Step 3: Commit**

```bash
git add docs/COLETA-CONDOMINIOS.md docs/LAI-CONDOMINIOS-VALPARAISO.md
git commit -m "docs: operacao da coleta e pedido de LAI"
```

---

### Task 7: Verificação final

- [ ] **Step 1: Rodar a suíte completa**

Run: `python manage.py test`
Expected: todos os testes passam (180 existentes + novos).

- [ ] **Step 2: Rodar lint e gates**

```bash
python -m ruff check .
python scripts/check_secrets.py
python scripts/check_security.py
python scripts/check_deploy.py
```

- [ ] **Step 3: Teste de fluxo completo com fixture**

Adicionar em `enderecos/test_coleta.py` um teste que:
1. cria zips de fixture;
2. chama `processar_parte`;
3. escreve CSV com `escrever_csv`;
4. chama `call_command("importar_condominios", ...)`;
5. confirma `Condominio.objects.filter(nome="...").exists()`.

- [ ] **Step 4: Commit final**

```bash
git add .
git commit -m "test(coleta): cobre fluxo completo com fixtures"
```
