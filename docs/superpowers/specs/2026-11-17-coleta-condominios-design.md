# Coleta de condomínios de Valparaíso de Goiás — desenho

**Data:** 2026-11-17
**Status:** aprovado na conversa (Q1–Q8 da rodada 2 e Q1–Q6 da rodada 3)

## Intenção

Popular o cadastro de `Condominio` com os condomínios residenciais de
Valparaíso de Goiás (GO), para que o cliente escolha no checkout em vez de
digitar o endereço. O que não for possível coletar automaticamente será
cadastrado manualmente pelo dono.

## Objetivos

- Coletar o maior número possível de condomínios residenciais, verticais e
  horizontais, do município.
- Gerar um CSV revisável, com procedência e marcação de revisão.
- Importar somente linhas revisadas, sem sobrescrever cadastro manual.
- Rodar localmente, sob demanda, sem tocar na VM de produção.

## Não objetivos

- Não raspar o Google Maps nem armazenar nome/endereço vindos dele em massa.
- Não calcular zona/taxa de entrega nesta fase.
- Não importar telefone/e-mail de síndico (LGPD e manutenção).
- Não guardar latitude/longitude nesta fase.
- Não distinguir blocos/torres do mesmo condomínio.
- Não criar integração recorrente com API paga.

## Restrições

- **Google Maps:** os Termos do Google Maps Platform (3.2.3) proíbem exportar,
  copiar ou armazenar nomes e endereços de estabelecimentos. O Maps só pode ser
  usado como conferência visual humana. `place_id` é a única exceção de cache.
- **OSM:** ODbL. O OSM entra apenas como pista de descoberta; o registro final
  é confirmado em CNPJ, prefeitura ou cadastro manual, para não transformar o
  banco em derivado de base OSM.
- **CNPJ:** Dados Abertos da Receita Federal, filtro por UF, município e CNAE
  8112-5/00 (condomínios prediais), situação ativa. Download grande; o script
  roda local e usa cache.
- **Modelo atual:** `nome`, `endereco`, `numero`, `bairro`, `cidade`, `cep`,
  `referencia`, `ativo`. `bairro` e `cidade` são obrigatórios.
- **Produção:** o CSV é revisado localmente; a importação roda com backup e
  `--dry-run` antes.

## Fontes

| Fonte | Papel | Cobertura |
|---|---|---|
| Receita Federal (CNPJ) | principal, automatizada | ~500–700 condomínios prediais ativos |
| OSM/Overpass | descoberta de horizontais e nomes | incerta, a validar |
| Prefeitura (LAI) | complemento oficial | horizontais e associações sem CNPJ |
| Cadastro manual | lacunas conhecidas | o que o dono conhece |

## Fluxo

```
CNPJ (Receita) ─┐
OSM (Overpass) ─┼─→ normalizar → dedup → dados/condominios.csv (revisar=nao)
Prefeitura ─────┘                              │
                                               ▼
                              dono revisa e marca revisado=sim
                                               │
                                               ▼
                         manage.py importar_condominios --dry-run
                                               │
                                               ▼
                         manage.py importar_condominios (produção)
```

## Regras de dado

### O que conta como condomínio

- Residencial vertical (edifícios) e horizontal (loteamentos fechados,
  residenciais, associações de moradores).
- Fora: condomínios comerciais e empresas administradoras.

### Blocos e torres

- `BLOCO 7`, `TORRE B`, `ENTRADA B`, `QUADRA 3` no nome do condomínio são
  colapsados em um único registro.
- Empreendimentos numerados diferentes (`Colinas 1`, `Colinas 2`) permanecem
  separados.

### Nome de exibição

1. Usar o nome fantasia do CNPJ, se existir e não for genérico.
2. Senão, limpar a razão social: remover `CONDOMINIO`, `CONDOMINIO DO`,
   `CONDOMINIO DO EDIFICIO`, `RESIDENCIAL`, `EDIFICIO`, `COND.`; remover
   sufixos de bloco/torre/entrada; converter `EDIFICIO` para `Edifício` e
   aplicar capitalização.
3. Guardar sempre `nome_origem` para auditoria.

### Deduplicação

- Chave: nome normalizado (sem acento, caixa baixa, sem prefixos e sem
  sufixos de bloco) + endereço + número + bairro.
- CNPJ tem precedência sobre OSM na mesma chave.
- Se o CNPJ trouxer vários blocos do mesmo condomínio, manter um registro e
  reportar os demais como duplicados.

### Campos ausentes

- Linha sem `nome`, `endereco`, `bairro` ou `cidade` vai para
  `dados/condominios-pendencias.csv`; não é importada.

## CSV de revisão

Delimitador `;`, codificação UTF-8 com BOM (abre no Excel), colunas:

```
nome;endereco;numero;bairro;cidade;cep;referencia;ativo;revisado;fonte;nome_origem;cnpj
```

- `revisado`: `nao` na coleta; o dono troca para `sim` após conferir.
- `ativo`: `sim` por padrão.
- `fonte`: `cnpj`, `osm`, `prefeitura`, `manual` ou `cnpj+osm`.
- `cnpj`: auditoria; não existe campo no modelo.

## Importação

- Comando `manage.py importar_condominios <csv>`.
- Só importa `revisado=sim` por padrão; `--incluir-nao-revisados` para
  emergência.
- Cria apenas o que não existe (create-only). Nunca atualiza nem apaga.
- `--dry-run` mostra o resumo sem gravar.
- Resumo: criados, existentes, ignorados por não revisados, pendências.
- Rodar em produção com backup do SQLite antes.

## Operação

- Coleta local, sob demanda; revisão trimestral.
- CNPJ com cache em `.cache-cnpj/`; o script pode apagar os zips após uso.
- OSM com retry e user-agent; endpoints alternativos.
- Nada de rodar o coletor na VM.

## Decisões tomadas

- Fonte A (CNPJ oficial + OSM/prefeitura/manual), sem lista paga.
- Manual pelo admin para o que o dono conhece.
- Sem telefone/e-mail, sem latitude/longitude, sem blocos.
- Validação por bairro em lotes; cobertura parcial aceita no primeiro ciclo.
- LAI à prefeitura em paralelo, opcional para o primeiro ciclo.

## O que fica para o implementador

- Nomes exatos de funções e comandos (ver plano).
- Formato interno dos arquivos da Receita (índices de coluna e encoding).
- Estratégia de download/streaming para não estourar disco.
- Texto do pedido de LAI.
