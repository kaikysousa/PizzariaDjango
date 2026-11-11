# Estoque e fichas técnicas

Operação de estoque do painel e cadastro de fichas técnicas no admin.

## Rotas

| Método | Rota | Uso |
| --- | --- | --- |
| GET | `/painel/estoque/` | Lista de ingredientes, saldos, mínimos, status e produtos sem ficha |
| GET/POST | `/painel/estoque/<int:pk>/ajustar/` | Ajuste manual de saldo do ingrediente |

As duas rotas exigem `is_staff`. Sem login de staff, o Django redireciona para a tela de login do admin.

## Lista de estoque

- Mostra ingrediente, unidade, saldo, mínimo, status, última movimentação e ação de ajuste.
- Destaca em vermelho os ingredientes ativos abaixo do mínimo.
- Filtra por status (`Abaixo do mínimo`, `No mínimo ou acima`, `Inativos`) e busca por nome.
- Lista os produtos disponíveis sem ficha técnica. O link abre o produto no admin para cadastrar os ingredientes.
- Produto sem ficha continua vendável. A aprovação do pedido não falha; o estoque daquele produto apenas não é baixado.

## Ajuste manual

Tipos permitidos:

- `entrada`: soma a quantidade ao saldo.
- `ajuste`: soma a quantidade ao saldo, com motivo operacional.
- `perda`: subtrai a quantidade do saldo.

Regras:

- quantidade maior que zero, com até três casas decimais;
- motivo obrigatório, com até 200 caracteres;
- usuário logado gravado em `MovimentoEstoque.criado_por`;
- saldo antes e depois exibidos na confirmação;
- `saida` e `estorno` não podem ser lançados manualmente: são gerados pelos serviços de pedido;
- toda alteração cria um `MovimentoEstoque` com `saldo_apos`. Nunca há alteração de saldo sem movimento.

O saldo pode ficar negativo. O painel sinaliza o ingrediente abaixo do mínimo.

## Fichas técnicas

No admin de produto existe o inline **Fichas técnicas**:

- ingrediente;
- quantidade;
- unidade (somente leitura, herdada do ingrediente).

Regras do modelo:

- quantidade maior ou igual a `0.001`;
- um ingrediente por produto (`unique_together` de produto e ingrediente);
- produto pode ter várias fichas.

Consumo aplicado pelos serviços já existentes:

- pizza inteira: `quantidade do item × quantidade da ficha`;
- meia pizza: `0,5 × quantidade do item × quantidade da ficha` de cada sabor;
- bebida ou produto sem ficha: sem baixa.

## Admin

- **Ingredientes**: saldo somente leitura (ajuste apenas pelo painel), mínimo, custo, ativo e filtros.
- **Fichas técnicas**: filtros por produto e ingrediente; quantidade editável na lista.
- **Movimentos de estoque**: somente leitura; filtros por tipo, ingrediente e data. Sem permissão de adicionar, alterar ou excluir.

## Testes

`estoque/tests.py` cobre:

- acesso ao painel apenas por staff;
- alerta de ingrediente abaixo do mínimo;
- entrada e perda alterando saldo e criando movimento;
- quantidade inválida e motivo vazio sem alteração;
- usuário logado no movimento;
- bloqueio de `saida` e `estorno` manuais;
- aviso de produto sem ficha;
- ficha duplicada e quantidade não positiva rejeitadas.

Comandos:

```bash
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py check
ruff check .
```
