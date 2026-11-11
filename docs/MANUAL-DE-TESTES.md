# Manual de testes — Gestão PizzariaDjango

Manual prático para validar a gestão da pizzaria no ambiente local, sem ler código.
Cobre pedido do cliente com aprovação, painel do dono, pedidos de balcão, condomínios,
estoque por ficha técnica e recibo térmico de 80 mm.

- [README](../README.md)
- [Especificação da gestão](ESPECIFICACAO-GESTAO.md)
- [Estoque e fichas técnicas](ESTOQUE.md)

> **Dados:** use somente dados fictícios. Não informe dados reais de clientes neste ambiente.

## 1. Pré-requisitos

| Item | Versão/uso |
| --- | --- |
| Windows 10/11 | Os comandos abaixo usam PowerShell; há equivalentes para `cmd` nas notas. |
| Python | 3.12 ou superior, com `pip`. |
| Git | Para clonar o repositório. |
| Chrome ou Edge | Necessário para o gate de recibo em PDF e para os testes visuais. |
| Impressora térmica 80 mm | Opcional. Sem ela, valide o recibo em PDF. |

Confira no PowerShell:

```powershell
python --version
git --version
```

Se `python` não for reconhecido, reinstale o Python marcando **Add python.exe to PATH** ou use
o caminho completo do executável. Use Python 3.12 ou superior, a versão suportada pelo projeto.

## 2. Instalação

```powershell
git clone https://github.com/kaikysousa/PizzariaDjango.git
cd PizzariaDjango
git switch feat/pizzaria-gestao

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

copy .env.example .env
notepad .env
```

No `cmd`, ative com `.venv\Scripts\activate.bat`.
Se o PowerShell bloquear a ativação, libere apenas a sessão atual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Confira o `.env`

O `.env.example` já vem com `DJANGO_DB_PATH=db.sqlite3`. Se a linha ficar vazia, o `migrate` falha com:

```text
django.core.exceptions.ImproperlyConfigured: settings.DATABASES is improperly configured.
Please supply the NAME value.
```

Abra o `.env` e mantenha:

```dotenv
DJANGO_DEBUG=1
DJANGO_DB_PATH=db.sqlite3
```

Mantenha `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost` para o ambiente local.
O `DJANGO_SECRET_KEY` de exemplo serve para desenvolvimento; não use em produção.

### Banco e dados iniciais

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

O `seed_demo` cria os produtos do cardápio e, se não existir nenhum pedido, um pedido de
demonstração. Ele imprime o token no final:

```text
SEED_DEMO_TOKEN=00000000-0000-0000-0000-000000000000
```

Guarde o token impresso: ele abre o acompanhamento e o recibo do pedido retornado pelo comando.

Abra:

- cardápio: <http://127.0.0.1:8000/>
- admin: <http://127.0.0.1:8000/admin/>
- painel: <http://127.0.0.1:8000/painel/>

Para recriar o pedido de demonstração use `python manage.py seed_demo --reset`.
Atenção: `--reset` apaga **todos** os pedidos antes de criar o novo.

## 3. Criar massa de teste

A massa abaixo produz números fáceis de conferir. Execute na ordem.

### 3.1 Usuários

1. Crie o dono com `python manage.py createsuperuser` (ou use o usuário já criado).
2. No admin, abra **Autenticação e Autorização → Usuários → Adicionar usuário**.
3. Crie `atendente` com senha `teste12345` e marque **Membro da equipe** (`is_staff`).
4. Crie `cliente` com senha `teste12345` e **não** marque **Membro da equipe**.
5. Salve.

O painel exige `is_staff`. O usuário `cliente` serve para o roteiro de segurança.

### 3.2 Produtos do seed

Abra **Admin → Pedidos → Produtos** e confira os seis produtos:

| Produto | Preço | Categoria |
| --- | ---: | --- |
| Margherita | 45,90 | Pizza |
| Calabresa | 49,90 | Pizza |
| Quatro Queijos | 52,90 | Pizza |
| Chocolate | 39,90 | Pizza doce |
| Coca-Cola 2L | 12,00 | Bebida |
| Água Mineral | 5,00 | Bebida |

Todos devem estar **Disponível**. O `seed_demo` usa `update_or_create`, então pode ser
executado novamente sem duplicar produtos.

### 3.3 Condomínio

Abra **Admin → Enderecos → Condominios → Adicionar condomínio** e preencha:

| Campo | Valor |
| --- | --- |
| Nome | Residencial Jardim das Flores |
| Endereço | Rua das Acácias |
| Número | 250 |
| Bairro | Jardim das Flores |
| Cidade | São Paulo |
| CEP | 01234-000 |
| Referência | Portaria principal |
| Ativo | Marcado |

Salve. O endereço completo gerado será:

```text
Rua das Acácias, 250 - Jardim das Flores - São Paulo - CEP 01234-000
```

### 3.4 Ingredientes

Abra **Admin → Estoque → Ingredientes → Adicionar ingrediente**. O campo **Estoque atual**
é somente leitura e começa em `0`; o saldo inicial entra no passo 3.5.

| Nome | Unidade | Estoque mínimo |
| --- | --- | ---: |
| Mussarela | Grama | 500 |
| Molho de tomate | Mililitro | 300 |
| Calabresa | Grama | 400 |
| Cebola | Grama | 200 |

Use **Salvar e adicionar outro** para agilizar. Deixe **Ativo** marcado.

### 3.5 Entrada inicial de estoque

O saldo só muda pelo painel de estoque, sempre com movimento registrado.

1. Abra <http://127.0.0.1:8000/painel/estoque/>.
2. Clique em **Ajustar** ao lado de cada ingrediente.
3. Em **Tipo de movimento**, escolha **Entrada**.
4. Informe a quantidade e um **Motivo** (obrigatório).
5. Clique em **Confirmar ajuste**.

| Ingrediente | Entrada | Motivo sugerido |
| --- | ---: | --- |
| Mussarela | 2000 | Carga inicial de teste |
| Molho de tomate | 1500 | Carga inicial de teste |
| Calabresa | 1200 | Carga inicial de teste |
| Cebola | 800 | Carga inicial de teste |

A mensagem de sucesso mostra o saldo antes e depois, por exemplo:
`Saldo: 0 → 2000 g.` A lista deve ficar com o selo **OK** nos quatro ingredientes.

### 3.6 Fichas técnicas

Abra **Admin → Pedidos → Produtos**, clique em **Margherita** e preencha o inline
**Fichas técnicas**:

| Produto | Ingrediente | Quantidade |
| --- | --- | ---: |
| Margherita | Mussarela | 200 |
| Margherita | Molho de tomate | 100 |
| Calabresa | Calabresa | 200 |
| Calabresa | Cebola | 50 |

A unidade é herdada do ingrediente e aparece somente para leitura. Salve cada produto.
Não repita o mesmo ingrediente no mesmo produto: o sistema rejeita a duplicidade.

### 3.7 Conferência da massa

Em <http://127.0.0.1:8000/painel/estoque/> confira:

- 4 ingredientes cadastrados;
- 0 ativos abaixo do mínimo;
- **Produtos sem ficha técnica** deve listar Quatro Queijos, Chocolate, Coca-Cola 2L e
  Água Mineral. Eles continuam vendáveis, mas não baixam estoque.

Em <http://127.0.0.1:8000/painel/> confira o painel **Dashboard**, com os cartões de status
e a seção **Ingredientes abaixo do mínimo** vazia.

## 4. Roteiros manuais

Cada roteiro informa objetivo, passos, resultado esperado e evidência sugerida.
O carrinho fica no `localStorage` do navegador e **não é limpo automaticamente** depois do
checkout. Para isolar um roteiro, use uma janela anônima ou remova os itens no carrinho antes
de começar.

### Rotas usadas nos roteiros

| Tela | URL | Acesso |
| --- | --- | --- |
| Cardápio | `/` | público |
| Revisar carrinho | `/carrinho/revisar/` | público, POST |
| Checkout | `/checkout/` | público |
| Acompanhamento | `/pedido/<token>/acompanhar/` | público, por token |
| Recibo | `/pedido/<token>/recibo/` | público, por token |
| Painel | `/painel/` | staff |
| Lista de pedidos | `/painel/pedidos/` | staff |
| Novo pedido de balcão | `/painel/pedidos/novo/` | staff |
| Detalhe do pedido | `/painel/pedidos/<pk>/` | staff |
| Editar pedido | `/painel/pedidos/<pk>/editar/` | staff |
| Ação de status | `/painel/pedidos/<pk>/acao/` | staff, POST |
| Estoque | `/painel/estoque/` | staff |
| Ajuste de estoque | `/painel/estoque/<pk>/ajustar/` | staff |
| Admin | `/admin/` | staff/superusuário |

A lista de pedidos aceita `?status=aguardando_aprovacao` e `?q=termo`.
A lista de estoque aceita `?status=abaixo`, `?status=ok`, `?status=inativos` e `?q=termo`.

### Status e ações

```text
aguardando_aprovacao -> aprovado -> preparando -> saiu -> entregue
                     -> cancelado
aprovado             -> cancelado
preparando           -> cancelado
```

| Status na tela | Valor interno | Ações disponíveis no painel |
| --- | --- | --- |
| Aguardando aprovação | `aguardando_aprovacao` | Aprovar pedido, Recusar pedido |
| Aprovado | `aprovado` | Iniciar preparo, Cancelar pedido |
| Preparando | `preparando` | Sair para entrega, Cancelar pedido |
| Saiu para entrega | `saiu` | Entregar |
| Entregue | `entregue` | Nenhuma |
| Cancelado | `cancelado` | Nenhuma |

Regras de estoque:

- a baixa acontece ao entrar em **Aprovado**;
- pizza inteira consome `quantidade do item × quantidade da ficha`;
- meia pizza consome `0,5 × quantidade do item × quantidade da ficha` de cada sabor;
- bebida e produto sem ficha não baixam estoque;
- cancelar um pedido **aprovado** estorna o consumo;
- cancelar um pedido em **preparando** não estorna; registre a perda manualmente se quiser;
- editar itens de um pedido aprovado estorna e reaplica, sem duplicar;
- o saldo pode ficar negativo e o painel alerta.

### 4.1 Cliente pede em condomínio

**Objetivo:** confirmar que o pedido do cliente nasce aguardando aprovação e não mexe no estoque.

**Passos:**

1. Abra <http://127.0.0.1:8000/> em uma janela anônima.
2. Clique em **Adicionar** no produto **Margherita**.
3. Clique em **Adicionar** em **Coca-Cola 2L**.
4. Clique em **Pedido** no topo e confira o painel **Seu pedido**.
5. Clique em **Revisar pedido**.
6. Em **Dados para entrega**, preencha **Nome** e **Telefone** com DDD.
7. Selecione **Condomínio** = `Residencial Jardim das Flores`.
8. Confira se o campo **Endereço** foi preenchido automaticamente.
9. Preencha **Complemento** com um valor fictício, por exemplo `Apto 42`.
10. Clique em **Finalizar pedido**.

**Resultado esperado:**

- a URL muda para `/pedido/<uuid>/acompanhar/`;
- o status é **Aguardando aprovação**;
- aparece o aviso de que o recibo será liberado após a aprovação;
- não aparece o botão **Ver recibo**;
- em `/painel/estoque/`, os saldos continuam iguais aos anotados antes do pedido;
- não existe movimento do tipo **Saída** com o motivo `Consumo do pedido #N`.

**Evidência:** print da tela de acompanhamento e anotação do total `R$ 57,90`
(45,90 + 12,00) e do número do pedido.

### 4.2 Dono aprova

**Objetivo:** aprovar o pedido, conferir a baixa de estoque e abrir o recibo.

**Passos:**

1. Abra <http://127.0.0.1:8000/admin/login/?next=/painel/> e entre com um usuário staff.
2. Abra <http://127.0.0.1:8000/painel/>.
3. Na seção **Aguardando aprovação**, clique no pedido do roteiro 4.1.
4. Confira cliente, condomínio, endereço, itens e total.
5. Clique em **Aprovar pedido**.
6. Confira o selo de status e a **Linha do tempo**.
7. Abra `/painel/estoque/` e depois a página **Ajustar** de **Mussarela**.
8. Confira **Últimos movimentos**.
9. Volte ao pedido e clique em **Imprimir recibo** (abre em nova aba).
10. Abra a página de acompanhamento do cliente e clique em **Ver recibo**.

**Resultado esperado:**

- o status passa para **Aprovado**;
- a mensagem confirma a mudança: `Pedido #N agora está em “Aprovado”.`;
- a linha do tempo registra **Pedido aprovado** e o usuário;
- Mussarela cai 200 g e Molho de tomate cai 100 ml para uma Margherita;
- os movimentos mostram **Saída** com motivo `Consumo do pedido #N` e `saldo_apos` correto;
- o recibo abre e mostra o status **Aprovado**;
- o cliente vê **Ver recibo** na página de acompanhamento.

**Evidência:** print do status e do movimento de saída; salve o PDF do recibo.

### 4.3 Dono recusa

**Objetivo:** recusar um pedido com motivo e conferir o cancelamento.

**Passos:**

1. Abra uma nova janela anônima e crie um pedido de cliente com **Água Mineral**,
   seguindo o mesmo fluxo do roteiro 4.1.
2. No painel, abra o pedido pendente.
3. No campo **Motivo para recusar pedido**, escreva `Fora da área de entrega`.
4. Clique em **Recusar pedido**.
5. Abra a página de acompanhamento do cliente.

**Resultado esperado:**

- o status fica **Cancelado**;
- o botão de recusa desaparece e nenhuma outra ação aparece;
- o detalhe do painel mostra **Motivo do cancelamento:** `Fora da área de entrega`;
- a página do cliente mostra **Este pedido foi cancelado.** e o motivo;
- o estoque não muda, pois o pedido nunca foi aprovado.

**Evidência:** print do detalhe com o motivo e da página de acompanhamento.

### 4.4 Pedido manual de balcão

**Objetivo:** criar um pedido de balcão, conferir o total calculado e a baixa imediata.

**Passos:**

1. Abra <http://127.0.0.1:8000/painel/pedidos/novo/>.
2. Preencha **Nome**, **Telefone** e **Endereço** (ou escolha o condomínio).
3. Em **Itens**, selecione **Margherita** na primeira linha.
4. Informe **Quantidade** `2`.
5. Clique em **Criar pedido**.

**Resultado esperado:**

- o pedido abre no detalhe com status **Aprovado**;
- **Origem** é **Balcão**;
- o total é `R$ 91,80` (2 × 45,90), calculado pelo servidor;
- o estoque já foi debitado: 400 g de Mussarela e 200 ml de Molho de tomate;
- o usuário logado aparece como aprovador na linha do tempo.

**Evidência:** print do detalhe com origem, total e status; anote os saldos antes e depois.

### 4.5 Meia pizza

**Objetivo:** montar meia pizza, conferir o preço médio e a baixa de metade de cada ficha.

**Passos:**

1. Abra o cardápio em uma janela anônima (ou limpe o carrinho).
2. Clique em **Meia** no produto **Margherita**.
3. Confira o aviso `Metade escolhida: Margherita. Escolha a segunda metade.`
4. Clique em **Meia** no produto **Calabresa**.
5. Abra **Pedido** e confira o item e o total.
6. Clique em **Revisar pedido**, preencha os dados e finalize.
7. No painel, abra o pedido e clique em **Aprovar pedido**.
8. Confira os movimentos de Mussarela, Molho de tomate, Calabresa e Cebola.

**Resultado esperado:**

- o item aparece como `Margherita / Calabresa`;
- o preço unitário é `R$ 47,90`, média de 45,90 e 49,90;
- após aprovar, a baixa é metade de cada ficha:
  - Mussarela: 100 g;
  - Molho de tomate: 50 ml;
  - Calabresa: 100 g;
  - Cebola: 25 g.

**Evidência:** print do carrinho com o item e o valor; print dos quatro movimentos.

### 4.6 Editar pedido antes de preparar

**Objetivo:** alterar os itens de um pedido aprovado sem duplicar a baixa.

**Passos:**

1. Use o pedido manual do roteiro 4.4, ainda em **Aprovado**.
2. Anote os saldos de Mussarela e Molho de tomate.
3. Clique em **Editar pedido**.
4. Altere a quantidade de Margherita de `2` para `1`.
5. Clique em **Salvar alterações**.
6. Confira o total e os movimentos dos dois ingredientes.

**Resultado esperado:**

- o total passa para `R$ 45,90`;
- o estoque final corresponde a **uma** pizza; a baixa não soma as duas versões;
- aparecem um **Estorno** dos 400 g/200 ml anteriores e uma nova **Saída** de 200 g/100 ml;
- o saldo final fica 200 g/100 ml menor que o saldo anterior à edição, sem duplicar.

**Evidência:** print do total e dos movimentos de estorno e saída.

### 4.7 Bloqueio após preparo

**Objetivo:** confirmar que os itens ficam travados depois de iniciar o preparo.

**Passos:**

1. No pedido do roteiro 4.6, clique em **Iniciar preparo**.
2. Confira o status **Preparando**.
3. Na seção **Itens**, confira o texto **Itens travados neste status.**
4. Clique em **Editar pedido**.
5. Confira o aviso **Itens em modo leitura** e a ausência dos campos de produto.
6. Volte ao detalhe e clique em **Sair para entrega**.
7. Clique em **Entregar**.

**Resultado esperado:**

- em **Preparando**, os itens não podem ser alterados; dados de cliente, entrega e pagamento
  permanecem editáveis;
- a sequência de status chega a **Entregue**;
- em **Entregue**, a seção **Ações** mostra **Nenhuma transição disponível para este status.**

**Evidência:** print da tela de edição em modo leitura e do status final.

### 4.8 Estoque baixo

**Objetivo:** deixar um ingrediente abaixo do mínimo e conferir o alerta.

**Passos:**

1. Abra <http://127.0.0.1:8000/painel/estoque/>.
2. Clique em **Ajustar** em **Mussarela**.
3. Escolha **Tipo de movimento** = **Perda**.
4. Informe uma quantidade que deixe o saldo abaixo de 500 g; por exemplo `1900`.
5. Informe o motivo `Perda simulada do manual`.
6. Clique em **Confirmar ajuste**.
7. Abra <http://127.0.0.1:8000/painel/>.

**Resultado esperado:**

- a mensagem mostra o saldo antes e depois;
- a lista de estoque destaca Mussarela com **Abaixo do mínimo**;
- o Dashboard mostra a seção **Ingredientes abaixo do mínimo** com Mussarela, saldo e mínimo;
- o alerta usa a regra `estoque_atual < estoque_minimo`; saldo exatamente igual ao mínimo
  **não** gera alerta.

**Evidência:** print do alerta no Dashboard e do movimento de perda.

### 4.9 Recibo de 80 mm

**Objetivo:** validar legibilidade, fonte maior e largura de 80 mm.

**Passos:**

1. Abra um pedido aprovado e clique em **Imprimir recibo**.
2. Confira a marca, o título, os itens, o total e o pagamento.
3. Clique em **Imprimir**.
4. No diálogo, escolha **Salvar como PDF**, papel de 80 mm (ou personalizado 80 × 297 mm),
   margens **Nenhuma**, escala **100%** e desmarque cabeçalho e rodapé.
5. Salve o PDF e abra-o.
6. Opcional: rode o gate automatizado descrito na seção 5.

**Resultado esperado:**

- nenhuma linha estoura a largura ou é cortada;
- a marca é maior que o corpo, e o total é o maior texto;
- a largura da página é 80 mm e o conteúdo cabe em uma página;
- pedidos com mais de 12 itens usam a página estendida de 420 mm; acima de 24 itens pode haver mais de uma página;
- o texto continua legível: corpo 13 px, marca 16 px, título 13 px, total 17 px;
- a margem lateral de impressão é de 2 mm.

**Evidência:** PDF salvo e print do diálogo de impressão. No gate, o resultado esperado é
`largura=80.1mm paginas=1` e `GATE_RECEIPT_80MM ok`.

### 4.10 Segurança

**Objetivo:** confirmar que o painel exige staff e que o cliente só acessa o próprio pedido.

**Passos:**

1. Abra uma janela anônima e acesse <http://127.0.0.1:8000/painel/>.
2. Confira o redirecionamento para `/admin/login/?next=/painel/`.
3. Entre com o usuário `cliente` (sem **Membro da equipe**).
4. Confirme que o painel não abre.
5. Entre com o usuário `atendente` ou o dono e confirme que o painel abre.
6. Copie a URL de acompanhamento de um pedido (`/pedido/<uuid>/acompanhar/`).
7. Abra essa URL em outra janela anônima, sem login.
8. Troque o UUID por outro UUID qualquer (inválido) e confira o 404.
9. Opcional: confira o cabeçalho do recibo:

```powershell
curl.exe -I "http://127.0.0.1:8000/pedido/COLE-O-TOKEN-AQUI/recibo/"
```

**Resultado esperado:**

- sem login, o painel redireciona para o login do admin;
- usuário sem `is_staff` não acessa o painel;
- staff acessa normalmente;
- o cliente acessa o pedido apenas pelo token UUID, sem login;
- token inexistente retorna **404**;
- o recibo responde com `X-Robots-Tag: noindex, nofollow`;
- todo POST do painel tem `csrfmiddlewaretoken` no formulário.

**Evidência:** prints do redirecionamento, do bloqueio do usuário comum e do cabeçalho do
recibo.

## 5. Testes automatizados

No PowerShell, com o ambiente virtual ativo:

```powershell
$env:DJANGO_DEBUG="1"
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py check
ruff check .
python scripts/check_receipt_pdf.py
```

No `cmd`, use `set DJANGO_DEBUG=1` na primeira linha.
O `DJANGO_DEBUG=1` também pode vir do `.env`; ele é necessário porque a suíte depende do modo
de desenvolvimento.

| Comando | O que cobre | Resultado esperado |
| --- | --- | --- |
| `python manage.py test` | Catálogo, carrinho, checkout, condomínios, status, painel, estoque, recibo, segurança e o fluxo E2E completo. | `Ran 160 tests` e `OK`. |
| `python manage.py makemigrations --check --dry-run` | Detecta modelo alterado sem migração. | `No changes detected`. |
| `python manage.py check` | Configuração e consistência do projeto. | `System check identified no issues (0 silenced).` |
| `ruff check .` | Estilo e erros estáticos de Python. | `All checks passed!`. |
| `python scripts/check_receipt_pdf.py` | Sobe um servidor temporário, imprime o recibo em PDF e mede a largura. | `largura=80.1mm paginas=1` e `GATE_RECEIPT_80MM ok`. |

Distribuição da suíte nesta branch:

| App | Testes | Foco |
| --- | ---: | --- |
| `pedidos` | 102 | catálogo, intake, status, condomínios, recibo, robustez, views e 12 testes E2E |
| `enderecos` | 3 | endereço completo e ordenação de condomínios |
| `estoque` | 27 | baixa, meia pizza, estorno, edição, ajustes manuais, admin |
| `painel` | 28 | autenticação, dashboard, lista, criação, edição e ações |
| **Total** | **160** | |

O gate do recibo precisa de Chrome ou Edge e das dependências de desenvolvimento
(`pypdf` e `websocket-client`, já incluídas em `requirements-dev.txt`). Ele usa as portas
`8798` e `9334`; feche outras execuções antes de rodá-lo.

A suíte E2E fica em `pedidos/tests/test_e2e_gestao.py` e está descrita em
[Testes automatizados](TESTES-AUTOMATIZADOS.md).

## 6. Solução de problemas

### Porta 8000 ocupada

Sintoma: `That port is already in use.` ou o servidor não inicia.

```powershell
python manage.py runserver 8001
```

Use `http://127.0.0.1:8001/` em todos os passos. Para encerrar o processo antigo no Windows,
feche o terminal onde ele está rodando ou use `Ctrl+C`.

### Banco sujo ou dados de teste inconsistentes

Para recomeçar sem apagar o banco principal, use outro arquivo:

```powershell
$env:DJANGO_DB_PATH="db-teste.sqlite3"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Para apagar o banco principal: pare o servidor, remova `db.sqlite3`, rode `migrate` e
`seed_demo` de novo. Isso apaga todos os pedidos e movimentos.

### Migração pendente

```powershell
python manage.py showmigrations
python manage.py makemigrations
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

Se o último comando não disser `No changes detected`, ainda há modelo sem migração.

### `ImproperlyConfigured: Please supply the NAME value`

Causa: `DJANGO_DB_PATH=` vazio no `.env`. Abra o `.env` e deixe
`DJANGO_DB_PATH=db.sqlite3`. Se preferir, remova a linha para usar o padrão `db.sqlite3`.
Depois rode `migrate` novamente.

### `DJANGO_SECRET_KEY é obrigatório quando DJANGO_DEBUG=0`

O `.env` não foi criado ou está com `DJANGO_DEBUG=0`. Copie `.env.example` para `.env` e
mantenha `DJANGO_DEBUG=1` no ambiente local.

### Chrome não encontrado no gate do recibo

O script procura:

```text
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
```

Instale Chrome ou Edge no caminho padrão ou valide o recibo manualmente pelo navegador.
Confira também se `pypdf` e `websocket-client` estão instalados:

```powershell
pip install -r requirements-dev.txt
```

### Impressora não aparece

1. Pareie a impressora no Windows em **Configurações → Bluetooth e dispositivos →
   Impressoras e scanners**.
2. Instale o driver do fabricante e confirme que a impressora não está offline.
3. No diálogo do navegador, selecione a impressora, papel de 80 mm, margens nenhuma e
   escala 100%.
4. O navegador não envia trabalhos por Bluetooth diretamente; o pareamento é do sistema.

Sem impressora física, valide em **Salvar como PDF** e com o gate automatizado.

### Fonte pequena mesmo depois do CSS

1. Recarregue com `Ctrl+F5` para descartar CSS antigo.
2. No diálogo de impressão, confira papel de 80 mm, escala 100% e **Nenhuma** margem.
3. Desmarque **Cabeçalhos e rodapés** e opções de “ajustar à página”.
4. Confira no DevTools que o recibo carregou `static/css/recibo.css`:
   corpo 13 px, marca 16 px, total 17 px.
5. Em produção, rode `python manage.py collectstatic` antes de servir os arquivos.

### Estoque negativo

É permitido pelo sistema. O painel alerta quando `estoque_atual < estoque_minimo`.
Confira os movimentos em **Admin → Estoque → Movimento estoques**, filtrando por
ingrediente ou motivo. Para repor, use **Ajustar → Entrada** com motivo.

### Pedido travado

Confira a tabela de status da seção 4. Só aparecem ações válidas para o status atual.
`Entregue` e `Cancelado` são finais. Se o pedido estiver no status errado, cancele (quando
permitido) e crie outro; não edite o banco manualmente.

Se o botão **Aprovar pedido** não aparecer, confirme que o usuário tem **Membro da equipe** e
que o pedido está em **Aguardando aprovação**. Recarregue a página após o login.

### Erro de CSRF ao enviar formulário

Sintoma: `CSRF verification failed. Request aborted.` A página ficou aberta por muito tempo
ou o cookie foi limpo. Recarregue o formulário e envie de novo; não desative a proteção CSRF.

### Itens antigos no carrinho

O carrinho fica no `localStorage` e não é limpo ao finalizar o pedido. Remova os itens pelo
botão **Remover** no carrinho ou use uma janela anônima. O link **Novo pedido** no recibo
também limpa o carrinho.

### `python` não reconhecido

Ative o ambiente virtual (`.venv\Scripts\Activate.ps1`) ou use o caminho completo
`.venv\Scripts\python.exe`. Confirme a versão com `python --version`; o projeto exige 3.12+.

## 7. Checklist final

Marque cada item depois de conferir a evidência.

### Instalação e massa

- [ ] Python 3.12+, Git e Chrome/Edge disponíveis.
- [ ] `.venv` criado e `requirements-dev.txt` instalado.
- [ ] `.env` criado com `DJANGO_DEBUG=1` e `DJANGO_DB_PATH=db.sqlite3`.
- [ ] `migrate` e `seed_demo` executados sem erro.
- [ ] Superusuário e usuário staff criados.
- [ ] Usuário comum `cliente` criado sem **Membro da equipe**.
- [ ] Condomínio `Residencial Jardim das Flores` cadastrado.
- [ ] Quatro ingredientes com entrada inicial e fichas de Margherita e Calabresa.
- [ ] Painel de estoque sem alertas e com os produtos sem ficha listados.

### Roteiros

- [ ] 4.1 Pedido de cliente em condomínio com endereço automático e status **Aguardando aprovação**.
- [ ] 4.1 Estoque inalterado antes da aprovação.
- [ ] 4.2 Aprovação com baixa de estoque, linha do tempo e recibo.
- [ ] 4.3 Recusa com motivo visível no painel e no acompanhamento.
- [ ] 4.4 Pedido de balcão **Aprovado**, origem **Balcão** e total correto.
- [ ] 4.5 Meia pizza com preço `R$ 47,90` e baixa de metade de cada ficha.
- [ ] 4.6 Edição sem duplicar baixa, com estorno e nova saída.
- [ ] 4.7 Itens travados em **Preparando** e fluxo até **Entregue**.
- [ ] 4.8 Alerta de estoque abaixo do mínimo no painel e no Dashboard.
- [ ] 4.9 Recibo em 80 mm, sem corte, com fonte maior e boa legibilidade.
- [ ] 4.10 Painel bloqueado sem login e para usuário sem `is_staff`.
- [ ] 4.10 Acompanhamento acessível apenas pelo token e recibo com `noindex`.

### Qualidade

- [ ] `python manage.py test` com 160 testes e `OK`.
- [ ] `python manage.py makemigrations --check --dry-run` com `No changes detected`.
- [ ] `python manage.py check` sem issues.
- [ ] `ruff check .` com `All checks passed!`.
- [ ] `python scripts/check_receipt_pdf.py` com `GATE_RECEIPT_80MM ok`.

### Evidências

- [ ] Prints ou PDFs dos roteiros salvos fora do repositório.
- [ ] Nenhum dado real de cliente usado.
- [ ] Nenhum arquivo `db.sqlite3`, `.env` ou PDF de teste commitado.
