# Sistema de Pedidos de Pizza

Uma aplicação web baseada em Django para gerenciar pedidos de pizza e bebidas. Este projeto fornece um sistema robusto para pizzarias gerenciarem seus itens de menu, receberem pedidos de clientes (incluindo pizzas meio a meio) e processarem pagamentos com uma interface amigável.

## Funcionalidades

- **Gerenciamento de Produtos**: Adicione e gerencie produtos de pizza e bebidas com categorias
- **Importação CSV**: Importe facilmente produtos de um arquivo CSV usando o script de importação fornecido
- **Pedidos de Meia Pizza**: Permita que os clientes selecionem dois sabores diferentes para uma única pizza
- **Gerenciamento Dinâmico de Carrinho**: Adicione, remova e ajuste pedidos em tempo real
- **Processo de Checkout**: Colete dados do cliente e finalize pedidos
- **Recibo de Pedido**: Gere e exiba recibos de pedidos com capacidade de impressão
- **Design Responsivo**: Interface baseada em Bootstrap que funciona em múltiplos dispositivos

## Requisitos

O projeto requer as seguintes dependências principais:
- Django 5.1.6
- Python 3.8+
- django-bootstrap5
- Outras dependências estão listadas em `requirements.txt`

## Instalação e Configuração

1. Clone o repositório:
```bash
git clone [repository-url]
cd [project-directory]
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Aplique as migrações do banco de dados:
```bash
python manage.py migrate
```

5. Crie um superusuário (opcional):
```bash
python manage.py createsuperuser
```

## Estrutura do Projeto

```
.
├── DjangoProject/           # Diretório principal do projeto
│   ├── settings.py          # Configurações do projeto
│   ├── urls.py              # Configuração principal de URLs
│   └── wsgi.py              # Configuração WSGI
├── pedidos/                 # Diretório principal da aplicação
│   ├── models.py            # Modelos de banco de dados (Produto, Categoria, Pedido)
│   ├── views.py             # Lógica de visualização para o sistema de pedidos
│   ├── urls.py              # Configuração de URLs da aplicação
│   └── migrations/          # Migrações do banco de dados
├── templates/               # Templates HTML
│   └── pedidos/
│       ├── index.html       # Página principal de listagem e pedido de produtos
│       ├── checkout.html    # Página de checkout do pedido
│       └── ticket.html      # Template de recibo/ticket do pedido
├── static/                  # Arquivos estáticos
│   └── css/
│       └── estilos.css      # Estilização personalizada para a aplicação
├── importar_produtos.py     # Script para importação de produtos a partir de CSV
├── cardapio.csv             # Arquivo CSV contendo dados dos produtos
├── manage.py                # Script de gerenciamento do Django
└── requirements.txt         # Dependências do projeto
```

## Funcionalidades Principais

### Gerenciamento de Produtos
- Produtos são organizados por categorias (Pizza, Bebida)
- Cada produto possui nome, preço, categoria e descrição opcional
- Produtos podem ser importados em massa a partir de um arquivo CSV

### Processamento de Pedidos
- Clientes podem navegar por produtos por categoria
- Para produtos de pizza, os usuários podem pedir pizzas inteiras ou combinar duas meias-pizzas
- Pedidos podem ser modificados em tempo real antes do checkout
- O botão "Limpar Pedido" permite resetar o pedido atual

### Fluxo de Checkout
- Clientes fornecem suas informações (nome, endereço, telefone)
- Detalhes do pedido são exibidos com o valor total
- Pedidos podem ser finalizados e um recibo é gerado
## Configuração

### Banco de Dados
O projeto usa SQLite3 como banco de dados padrão. A configuração está em `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Arquivos Estáticos
Arquivos estáticos são configurados em settings.py:

```python
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

## Configuração de Desenvolvimento

1. Configure seu ambiente de desenvolvimento:
- Defina `DEBUG = True` em settings.py para desenvolvimento
- Garanta que todas as variáveis de ambiente necessárias estejam configuradas
- Configure seu IDE/editor com linting e formatação adequados

2. Instale ferramentas de desenvolvimento:
```bash
pip install black flake8  # Opcional, mas recomendado
```

## Executando o Projeto

1. Inicie o servidor de desenvolvimento:
```bash
python manage.py runserver
```

2. Acesse a aplicação:
- Aplicação principal: http://localhost:8000
- Interface de administração: http://localhost:8000/admin

3. Importe produtos do CSV:
```bash
python importar_produtos.py
```

4. Para desenvolvimento:
- Faça migrações após alterações no modelo: `python manage.py makemigrations`
- Aplique migrações: `python manage.py migrate`
- Colete arquivos estáticos: `python manage.py collectstatic`

## Modelos

### Categoria
Representa categorias de produtos (Pizza, Bebida, etc.)
- `nome`: Nome da categoria

### Produto
Representa itens do menu
- `nome`: Nome do produto
- `preco`: Preço
- `categoria`: Chave estrangeira para Categoria
- `descricao`: Descrição opcional do produto

### Pedido
Representa pedidos dos clientes
- `cliente`: Nome do cliente
- `endereco`: Endereço de entrega
- `telefone`: Número de telefone para contato
- `produtos`: Campo de texto armazenando detalhes do pedido
- `total`: Valor total do pedido
- `data`: Data do pedido
- `pago`: Status do pagamento

## Formato de Importação CSV

O sistema suporta a importação de produtos a partir de um arquivo CSV com o seguinte formato:
```
nome,preco,categoria,descricao
"Margherita",25.90,Pizza,"Pizza tradicional com molho de tomate e queijo"
"Coca-Cola 2L",8.90,Bebida,""
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
