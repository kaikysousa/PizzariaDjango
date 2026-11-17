# Coleta de condomínios de Valparaíso de Goiás

Guia operacional do coletor e da importação. Rode tudo **na sua máquina**,
nunca na VM de produção.

## O que ele faz

1. Baixa os Dados Abertos do CNPJ da Receita Federal e filtra:
   - UF `GO`;
   - município `VALPARAISO DE GOIAS`;
   - CNAE `8112-5/00` (condomínios prediais);
   - situação cadastral ativa (`02`).
2. Consulta o OpenStreetMap (Overpass) para achar residenciais horizontais.
3. Junta as fontes, remove duplicados e gera:
   - `dados/condominios.csv` — lista para revisão;
   - `dados/condominios-pendencias.csv` — linhas sem bairro/cidade/endereço;
   - `dados/condominios-cnpj.csv` e `dados/condominios-osm.csv` — brutos.

## Limites importantes

- **Google Maps não é usado por código.** Os termos proíbem copiar e guardar
  nomes/endereços de estabelecimentos. Use o Maps só para conferir visualmente.
- **OSM é pista, não fonte final.** Confirme o registro em CNPJ, prefeitura ou
  cadastro manual.
- O CNPJ cobre principalmente **condomínios prediais**. Horizontais e
  associações de moradores podem não ter CNAE 8112-5/00; entram por OSM, LAI ou
  cadastro manual.
- O download completo do CNPJ tem **vários GB** (10 pares de arquivos). O
  script guarda cache em `.cache-cnpj/`; a primeira execução demora.
- O volume esperado é de **500 a 700** registros, não dezenas.

## Pré-requisitos

- Python 3.12 com o venv do projeto.
- Internet.
- Espaço em disco para o cache (vários GB) ou paciência para baixar parte por
  parte.

## Coleta

```powershell
.venv\Scripts\activate

# tudo: CNPJ + OSM + merge
python scripts/coletar_condominios.py --fonte tudo

# só CNPJ (se o OSM estiver fora)
python scripts/coletar_condominios.py --fonte cnpj

# só OSM
python scripts/coletar_condominios.py --fonte osm
```

Opções úteis:

```text
--saida-dir dados          pasta dos CSVs
--cache-dir .cache-cnpj    cache dos zips da Receita
--partes 0-9               partes do CNPJ (use 0-0 para testar uma)
--municipio "VALPARAISO DE GOIAS"
--uf GO
--cnae 8112500
--bbox "-16.12,-48.03,-16.01,-47.92"
--url-base "https://dadosabertos.rfb.gov.br/CNPJ/"
```

Se a Receita estiver fora ou bloquear a rede, troque `--url-base` por um
espelho dos mesmos arquivos. O script usa cache: um arquivo já baixado não é
baixado de novo.

Se o OSM falhar, o comando `tudo` continua e gera o CSV só com o CNPJ.

## Revisão do CSV

Abra `dados/condominios.csv` no LibreOffice ou Excel.

- O arquivo usa `;` e UTF-8 com BOM; deve abrir em colunas.
- Confira nome, endereço, número, bairro e CEP.
- Corrija nomes ruins (`CONDOMINIO DO EDIFICIO X` → `Edifício X`).
- Blocos/torres do mesmo condomínio devem virar uma linha; `Colinas 1` e
  `Colinas 2` continuam separados.
- Troque `revisado` de `nao` para `sim` nas linhas conferidas.
- Se for salvar pelo Excel, use **CSV UTF-8 (separado por ponto e vírgula)**.
  Salvar como CSV comum (vírgula) quebra a importação.

Para o que não estiver na lista, cadastre pelo admin:
`/admin/enderecos/condominio/add/`. O importador nunca sobrescreve esse
cadastro.

## Importação

Sempre com backup e dry-run:

```bash
cd /home/ubuntu/pizzaria
sqlite3 db.sqlite3 ".backup '/home/ubuntu/backups/db-$(date +%F-%H%M%S).sqlite3'"
.venv/bin/python manage.py importar_condominios /caminho/condominios.csv --dry-run
.venv/bin/python manage.py importar_condominios /caminho/condominios.csv
```

Saída esperada:

```text
criados=123 existentes=4 ignorados=0 pendencias=2
```

- `criados`: novos condomínios.
- `existentes`: já estavam no banco (não duplica).
- `ignorados`: `revisado=nao` (padrão).
- `pendencias`: faltou nome, endereço, bairro ou cidade.

Para importar linhas não revisadas (não recomendado):
`--incluir-nao-revisados`.

## Problemas comuns

| Sintoma | Causa | Correção |
|---|---|---|
| `HTTP 403/000` na Receita | site fora ou bloqueio de rede | tente de novo; use outra rede |
| Overpass indisponível | API lenta/fora | rode `--fonte cnpj` e tente o OSM depois |
| CSV inteiro em uma coluna | Excel salvou com vírgula | salve como CSV UTF-8 com `;` |
| Acentos quebrados no Excel | arquivo sem BOM | use o CSV gerado pelo script |
| Muitos duplicados | nome/endereço divergentes | ajuste o nome na revisão e rode o dry-run |
| Linha sumiu | foi para pendências | veja `condominios-pendencias.csv` |

## Rotina sugerida

- Primeiro ciclo: CNPJ + OSM, revisão por bairro (Ypiranga, Anhanguera,
  Esplanada primeiro).
- Depois: revisão trimestral; rode o coletor de novo e importe só o que falta.
- Condomínios novos: cadastro manual no admin ou acrescente no CSV.
