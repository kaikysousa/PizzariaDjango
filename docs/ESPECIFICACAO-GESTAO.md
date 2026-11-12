# Especificação — Gestão PizzariaDjango

## Objetivo

Evoluir o PizzariaDjango de cardápio/checkout para um sistema de gestão com:

- pedido de cliente com aprovação da loja;
- pedido de balcão criado pelo dono;
- painel do dono para aprovar, recusar, editar e avançar pedidos;
- cadastro de condomínios para preencher endereço;
- controle opcional de estoque por ingrediente e ficha técnica;
- recibo térmico com fonte maior.

## Fora de escopo

- Deploy em produção.
- Gateway de pagamento.
- Login de cliente.
- Taxa de entrega por condomínio.
- Notificações WhatsApp/email.
- Multiempresa.
- Bloqueio de pedido por estoque insuficiente.
- Edição de itens depois que o pedido entra em `preparando`.
- Reescrever o admin do Django.

## Fluxos

### Cliente

1. Monta carrinho.
2. Vai para checkout.
3. Escolhe condomínio ativo.
4. Endereço é preenchido automaticamente; pode complementar.
5. Envia pedido.
6. Pedido nasce `aguardando_aprovacao`, origem `cliente`.
7. Redireciona para página de acompanhamento por token.
8. Quando aprovado, página libera link do recibo.

### Dono/loja

1. Acessa `/painel/` com usuário `is_staff`.
2. Vê pedidos pendentes e em andamento.
3. Aprova, recusa com motivo, ou avança status.
4. Pode criar pedido manual com origem `balcao`; nasce `aprovado`.
5. Pode editar pedido enquanto itens estiverem editáveis.
6. Pode ajustar estoque e ver movimentos.
7. Pode imprimir recibo.

## Status do pedido

```text
aguardando_aprovacao -> aprovado -> preparando -> saiu -> entregue
                     -> cancelado
aprovado             -> cancelado
preparando           -> cancelado
```

- `cancelado` é final.
- `entregue` é final.
- Transições inválidas retornam erro.
- Cancelamento depois de `aprovado` estorna estoque.
- Cancelamento depois de `preparando` não estorna; registrar perda se o dono quiser.

## Modelos

### enderecos.Condominio

- `nome` CharField(120)
- `endereco` CharField(150)
- `numero` CharField(20, blank)
- `bairro` CharField(80)
- `cidade` CharField(80)
- `cep` CharField(9, blank)
- `referencia` CharField(150, blank)
- `ativo` BooleanField(default=True)
- `criado_em`, `atualizado_em`
- `endereco_completo` property
- ordering por nome

### pedidos.Pedido — campos novos

- `origem`: `cliente` | `balcao`, default `cliente`
- `condominio`: FK `enderecos.Condominio`, null, blank, `on_delete=SET_NULL`
- `condominio_nome`: CharField(120), blank; nome livre quando não há cadastro
- `aprovado_por`: FK usuário, null, blank
- `aprovado_em`: DateTimeField null, blank
- `motivo_cancelamento`: TextField blank
- `status`: substituir `novo` por `aguardando_aprovacao`

### estoque.Ingrediente

- `nome` CharField(100)
- `unidade`: `g` | `ml` | `un`
- `estoque_atual` Decimal(10,3), default 0
- `estoque_minimo` Decimal(10,3), default 0
- `custo_unitario` Decimal(10,4), null, blank
- `ativo` BooleanField(default=True)
- ordering por nome
- property `abaixo_minimo`

### estoque.FichaTecnica

- `produto` FK `pedidos.Produto`, related_name `ficha_tecnica`
- `ingrediente` FK `estoque.Ingrediente`, related_name `fichas`
- `quantidade` Decimal(10,3)
- unique_together (`produto`, `ingrediente`)
- validação: quantidade > 0

### estoque.MovimentoEstoque

- `ingrediente` FK
- `tipo`: `entrada` | `saida` | `ajuste` | `perda` | `estorno`
- `quantidade` Decimal(10,3)
- `saldo_apos` Decimal(10,3)
- `pedido` FK `pedidos.Pedido`, null, blank
- `motivo` CharField(200), blank
- `criado_por` FK usuário, null, blank
- `criado_em` auto_now_add
- ordering `-criado_em`

## Regras de estoque

- Baixa ao entrar em `aprovado`.
- Pizza inteira: consome `quantidade_item * quantidade_ficha`.
- Meia pizza: consome `0.5 * quantidade_item * quantidade_ficha` de cada sabor.
- Bebida: sem ficha, sem baixa.
- Produto sem ficha: não falha; retorna aviso.
- Cancelamento após aprovação: estorna movimentos de saída do pedido.
- Edição de itens após aprovação: estorna e reaplica; nunca duplicar.
- Estoque pode ficar negativo; painel alerta.
- Ajuste manual sempre gera movimento.
- Toda operação usa `transaction.atomic` e `select_for_update`.

## Serviços

### pedidos/services.py

- `criar_pedido(...)` aceita `origem`, `condominio`, `condominio_nome`, `status_inicial`.
- `alterar_status(pedido, novo_status, usuario=None, motivo="")` valida transição, grava aprovação/cancelamento e emite `pedido_status_alterado`.
- `atualizar_itens_pedido(pedido, itens, usuario=None)` permitido só se `pedido.itens_editaveis`; recalcula total; emite `pedido_itens_alterados`.
- `pedido.itens_editaveis`: status em `aguardando_aprovacao` ou `aprovado`.

### pedidos/signals.py

- `pedido_status_alterado = Signal()`
- `pedido_itens_alterados = Signal()`

### estoque/services.py

- `registrar_movimento(...)`
- `consumir_pedido(pedido, usuario=None) -> list[str]` avisos
- `estornar_pedido(pedido, usuario=None)`
- `reprocessar_pedido(pedido, usuario=None)`
- receivers de `pedido_status_alterado` e `pedido_itens_alterados`

## Rotas

### Públicas

- `/` cardápio
- `/carrinho/revisar/`
- `/checkout/`
- `/pedido/<uuid:token>/acompanhar/` acompanhamento
- `/pedido/<uuid:token>/recibo/` recibo

### Painel

- `/painel/` dashboard
- `/painel/pedidos/` lista com filtros
- `/painel/pedidos/novo/` pedido manual
- `/painel/pedidos/<int:pk>/` detalhe
- `/painel/pedidos/<int:pk>/editar/`
- `/painel/pedidos/<int:pk>/acao/` POST de transição
- `/painel/estoque/` lista e alertas
- `/painel/estoque/<int:pk>/ajustar/` POST de ajuste

### Admin

- `/admin/` para CRUD de produtos, condomínios, ingredientes, fichas e movimentos.

## Permissões

- Painel exige `is_staff`.
- Cliente acessa só o próprio pedido por token.
- Recibo continua `noindex`.
- CSRF em todos os POSTs.
- Nunca confiar em total vindo do cliente.

## Recibo

- Base `13px`, line-height `1.45`.
- Marca `16px`.
- Título `13px`.
- Total `17px`.
- Padding lateral `2mm`.
- Testar PDF em 80 mm; nenhuma linha pode estourar.

## Qualidade

- `python manage.py test` verde.
- `python manage.py makemigrations --check --dry-run` sem mudanças.
- `python manage.py check`.
- `ruff check .`.
- Testes novos para status, condomínio, estoque, painel, recibo.
- Nenhum segredo versionado.
- Migrações reversíveis.

## Branches

- Integração: `feat/pizzaria-gestao`
- Fundação: `feat/gestao-fundacao`
- Checkout/condomínios: `feat/gestao-checkout-condominios`
- Painel/pedidos: `feat/gestao-painel-pedidos`
- Estoque: `feat/gestao-estoque`
- Recibo: `feat/gestao-recibo`
- E2E: `test/gestao-e2e`
- Manual: `docs/gestao-manual`
- Revisão: `review/gestao-final`
- Correções da revisão: `fix/gestao-revisao`

## Regras para subagentes

- Trabalhar em worktree próprio.
- Nunca commitar em `main` ou em `feat/pizzaria-gestao`.
- Nunca abrir PR.
- Push apenas da própria branch.
- Não alterar arquivos fora do escopo.
- Rodar testes antes de cada commit.
- Devolver resumo, comandos rodados, riscos e arquivos alterados.
