# Sistema de Pedidos — Pizzaria

Aplicação Django para cardápio, carrinho, checkout e impressão de recibo em impressora térmica de 80 mm.

## Funcionalidades

- Cardápio com busca, filtro por categoria e paginação.
- Carrinho no navegador, com meia pizza (dois sabores).
- Checkout com dados do cliente e forma de pagamento.
- Pedido persistido com itens normalizados e total recalculado no servidor.
- Recibo de 80 mm pronto para impressão pelo navegador.
- Administração de produtos e pedidos no Django admin.

## Requisitos

- Python 3.12+
- Django 5.1.6
- Impressora térmica de 80 mm pareada no Windows (para impressão física)

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra `http://127.0.0.1:8000/`. O admin fica em `/admin/`.

## Variáveis de ambiente

| Variável | Padrão | Uso |
|---|---|---|
| `DJANGO_DEBUG` | `1` | `0` em produção |
| `DJANGO_SECRET_KEY` | vazio | obrigatória quando `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | hosts separados por vírgula |
| `DJANGO_DB_PATH` | `db.sqlite3` | caminho do banco SQLite |
| `DJANGO_SECURE_SSL_REDIRECT` | `1` | redireciona HTTP para HTTPS em produção |
| `DJANGO_HSTS_SECONDS` | `3600` | HSTS em produção |

## Testes

```bash
python manage.py test
```

Os gates de auditoria ficam em `GATES.md` e podem ser verificados com a skill `unlazy`.

## Impressão

1. Pareie a impressora térmica no Windows e instale o driver.
2. Abra o recibo de um pedido e clique em **Imprimir**.
3. No diálogo do navegador, selecione a impressora e papel de 80 mm.
4. O CSS usa `@page { size: 80mm auto; margin: 0 }`; o driver deve respeitar a largura.

O navegador não envia trabalho por Bluetooth diretamente. O pareamento e o driver são do sistema operacional.

## Estrutura

```
DjangoProject/        configuração
pedidos/              app: models, services, views, forms, admin, tests
templates/            base, cardápio, checkout e recibo
static/css/           tokens, estilos e CSS do recibo
static/js/            carrinho e motion
scripts/              gates de auditoria
```

## Limitações

- Não processa pagamento online; registra a forma escolhida.
- Não emite documento fiscal. O CNPJ é configuração e não vem preenchido.
- Não há autenticação de cliente; o recibo usa token UUID.
- SQLite é o banco padrão de desenvolvimento.
