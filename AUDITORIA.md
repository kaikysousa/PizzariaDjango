# Auditoria — Pizzaria Django

Data: 27/10/2026  
Commit auditado: `ea4b2d9`  
Escopo: fase 1, somente leitura. Nenhum código de aplicação foi alterado.

## 1. Resumo executivo

O projeto tem uma base Django simples e funcional, mas o fluxo principal não fecha: o formulário de checkout não envia nada, então nenhum pedido chega ao banco. A impressão de 80 mm também não está garantida — o PDF gerado sai em 215,9 × 279,4 mm porque falta `@page`. O backend confia no total enviado pelo navegador e aceita um pedido de R$ 0,01. O visual tem problemas objetivos: botão de meia pizza aparece em bebidas, paginação morta, IDs duplicados, filtros estourando no mobile e dois frameworks CSS conflitantes. Segurança precisa de correção antes de qualquer deploy: `SECRET_KEY` versionada, `DEBUG=True` e IP público em `ALLOWED_HOSTS`. Não há nenhum teste.

## 2. Método e evidência

- `understand`: pipeline completo não executado. O plugin exige `pnpm`, que não está instalado; o mapeamento foi feito por leitura direta dos 38 arquivos versionados.
- `code-review`: dois eixos em paralelo (Standards e Spec), sobre a árvore inteira.
- `caveman-review`: segunda passada curta nos arquivos críticos.
- `computer-use`: indisponível. O runtime do Orca não estava rodando (`runtime_unavailable`). O teste local foi feito com Chrome headless via CDP, no mesmo navegador e no mesmo DOM.
- `research`: fatos de impressão e Bluetooth confirmados no MDN.
- `improve-codebase-architecture`: relatório visual em `C:\Users\wisla\AppData\Local\Temp\opencode\architecture-review-20261027.html`.
- `writing-plans`: plano por fases na seção 7, adaptado para o entregável único desta auditoria.

Ambiente de teste: venv temporário com Django 5.1.6, banco SQLite em `%TEMP%`, servidor em `127.0.0.1:8765`, 5 produtos semeados.

## 3. Achados

Severidade: P0 quebra o fluxo ou expõe segredo; P1 corrompe dados ou bloqueia uso real; P2 degrada qualidade; P3 manutenção.

| ID | Sev | Local | Problema | Impacto | Correção |
|---|---|---|---|---|---|
| P0-01 | P0 | `templates/pedidos/checkout.html:102`, `pedidos/views.py:34-43` | `<form>` sem `method`, `action` ou `{% csrf_token %}`; nenhum submit existe. O ramo POST da view é código morto. | Nenhum pedido é persistido pela interface. Fechar o pedido só imprime. | Form POST para `checkout`, CSRF, botão submit e redirect PRG. |
| P0-02 | P0 | `templates/pedidos/checkout.html:7-90` | Falta `@page { size: 80mm auto; margin: 0 }`. | O navegador usa Letter/A4. PDF medido: 215,9 × 279,4 mm. A nota não sai em 80 mm. | Adicionar `@page` e testar o PDF em 80 mm. |
| P0-03 | P0 | `DjangoProject/settings.py:23,26,28-32` | `SECRET_KEY` literal versionada, `DEBUG=True`, IP público `34.39.141.209` em `ALLOWED_HOSTS`. | Se o IP estiver ativo, qualquer erro expõe stack trace e a chave permite forjar sessões. | Mover segredo para ambiente, `DEBUG=False` em produção, hosts explícitos. |
| P1-01 | P1 | `pedidos/views.py:40-42`, `checkout.html:143-149` | O servidor grava o `total` enviado pelo cliente, sem recalcular. Teste: pedido de R$ 45,90 gravado com `total=0.01`. | Fraude de preço e divergência entre recibo e banco. | Recalcular com preços do banco dentro de uma transação. |
| P1-02 | P1 | `pedidos/views.py:42` | `total=""` chega ao `DecimalField` e levanta `ValidationError`. | Erro 500 em POST incompleto. | Formulário Django + validação, retorno 400 e mensagem. |
| P1-03 | P1 | `templates/pedidos/index.html:45,46,47,103` | `id="pedido"` duplicado (span e ul) e `id="total-pedido"` duplicado. | `getElementById` pega só o primeiro; o segundo total nunca atualiza e o contador é apagado pela lista. | IDs únicos e um único ponto de render. |
| P1-04 | P1 | `templates/pedidos/index.html:77` | `{% if product.categoria == "pizza" or "pizza doce" %}`: string não vazia é truthy. | "Adicionar meia" aparece em bebidas e em tudo. Confirmado na captura. | `{% if product.categoria in "pizza,pizza doce" %}` ou `Categoria` com choices. |
| P1-05 | P1 | `pedidos/views.py:28-31`, `index.html:90-102` | `Paginator` criado e descartado; template chama `has_previous` em QuerySet. | Paginação morta: 5 produtos exibidos com `Paginator(..., 4)`. | Passar `page_obj` e usar `page_obj` no template. |
| P1-06 | P1 | `static/css/estilos.css:116-119` | `.filtros` é `flex` sem `flex-wrap`. | Botões estouram a tela no mobile; "Remove a filtragem" fica cortado. | `flex-wrap: wrap` e largura mínima por botão. |
| P1-07 | P1 | `templates/pedidos/index.html:10-11,115` | Bootstrap 4.6.2 e Bootswatch 5 Lux carregados juntos; JS é Bootstrap 4. | Componentes e variáveis CSS conflitam; aparência imprevisível. | Escolher uma versão e remover a outra. |
| P1-08 | P1 | `templates/pedidos/checkout.html:153-156` | `imprimirNota()` chama `window.print()` e limpa o carrinho em seguida. | Cancelar a impressão apaga o pedido mesmo assim. | Limpar só após confirmação explícita. |
| P1-09 | P1 | `pedidos/tests.py` | Arquivo vazio; `manage.py test` roda 0 testes. | Nenhuma regressão é detectada. | Testes de intake, total, paginação e impressão. |
| P2-01 | P2 | `index.html:75`, `checkout.html:145` | Preço cru `45.90`, ponto decimal, sem `R$`; total em `toFixed(2)`. | Leitura ambígua e fora do padrão pt-BR. | `R$ 45,90` com `Decimal`/Intl e `data-*` para o JS. |
| P2-02 | P2 | `importar_produtos.py:4` | Caminho Linux fixo e ausência de `django.setup()`. | Script falha no Windows: `ImproperlyConfigured`. | `Path(__file__)` e `django.setup()`. |
| P2-03 | P2 | `DjangoProject/urls.py:29` | Serve `STATIC_URL`, mas `MEDIA_URL`/`MEDIA_ROOT` existem. | Imagens de produto nunca são servidas em desenvolvimento. | `static(settings.MEDIA_URL, ...)`. |
| P2-04 | P2 | `README.md:61-69,143,153-172` | Documenta `ticket.html`, modelo `Categoria`, telefone, `pago` e `django-bootstrap5`; nada existe. | Onboarding e manutenção partem de fatos falsos. | Atualizar README ou implementar o que ele promete. |
| P2-05 | P2 | `pedidos/models.py:4-8` | `Produto` sem `Meta.ordering`. | Ordem instável entre páginas e execuções. | `ordering = ["nome"]` ou campo de posição. |
| P2-06 | P2 | `estilos.css:81-84,131-137` | Texto branco em `#ffc107`, `#ff5733`, `#3498db`. | Contraste abaixo de 4,5:1; ilegível sob luz forte. | Texto escuro ou fundo mais escuro. |
| P2-07 | P2 | `index.html:3-5` | `lang="en"`, `<title>Title</title>`, sem meta description. | Acessibilidade e SEO ruins. | `lang="pt-BR"`, título e descrição reais. |
| P2-08 | P2 | raiz | Versionados: `.idea/`, `gunicorn-error-log`, `templates/pedidos/index.html.save`. | Ruído, segredos de IDE e risco de editar arquivo errado. | Remover do índice e ignorar. |
| P2-09 | P2 | `index.html:222-232` | Funções `filtroPizza`, `filtroBebidas`, `filtroDoces` mortas e com valores trocados. | Código enganoso. | Remover. |
| P2-10 | P2 | `index.html:162-200` | Meia pizza usa `sessionStorage` sem indicar a metade pendente nem permitir cancelar. | Usuário fica sem feedback e não consegue desfazer. | Estado visível com "metade selecionada" e botão cancelar. |
| P2-11 | P2 | `checkout.html:97` | CNPJ fictício `00.000.000/0000-00` e nome fixo. | Nota fiscal falsa se impressa como está. | Dados reais por configuração. |
| P3-01 | P3 | `pedidos/views.py:2,4,5`; `urls.py:20,22` | Imports duplicados e `forms` morto. | Ruído. | Limpar. |
| P3-02 | P3 | `models.py:10-16` | `items` como `CharField(3000)`; `observacoes` obrigatório; sem `__str__`. | Sem integridade de itens e admin ilegível. | `ItemPedido` + `__str__` + `blank=True`. |
| P3-03 | P3 | `models.py:5,7` | Sem índices em `nome`/`categoria`. | Busca e filtro degradam com volume. | `db_index` ou `Index`. |
| P3-04 | P3 | `index.html:22-25` | Navbar só com "Limpar pedido". | Hierarquia visual vazia; ação destrutiva em destaque. | Navbar com marca e navegação; limpar em menu secundário. |
| P3-05 | P3 | `index.html:92,96,100` | URLs `?page= {{ ... }}` com espaço. | Link vira `page=%20N`; paginação quebraria mesmo se ativa. | `?page={{ ... }}`. |
| P3-06 | P3 | `index.html:244`; `checkout.html:129` | `</script>` depois de `</body>`; `type="button"onclick` sem espaço. | HTML inválido em casos de borda. | Corrigir estrutura. |
| P3-07 | P3 | `migrations/0003_alter_produto_imagem.py:15-19` | `imagem` virou `CharField(default=2)` e foi removida em `0006`. | Histórico de migração sem sentido para quem lê. | `squashmigrations` quando estabilizar. |

### Suspeitas descartadas

- **Total ignora quantidade:** falso. O campo `[2]` guarda o total da linha. Dois cliques em Margherita produziram `[2, "Margherita", 91.8]`, e o checkout somou `103.80` com a bebida. O problema é o nome `preco`, não o cálculo.
- **`@media print` com chaves erradas:** falso. As chaves fecham. O bloco `label` está dentro do `@media print`, o que parece intencional, apesar da indentação enganosa.
- **Import `from django.conf.urls import static` quebra o app:** falso. Importa o módulo `django.conf.urls.static`; `manage.py check` passa sem erros.
- **`urls.py` serve mídia errada:** parcialmente verdadeiro. O `static()` correto é importado e usado, mas só para `STATIC_URL`; `MEDIA_URL` fica sem rota.

## 4. Visual

Capturas: `%TEMP%\opencode\shots\index-desktop.png`, `index-mobile.png`, `checkout-desktop.png`, `checkout-mobile.png`.

- Cardápio em grade fixa `col-md-3`: o quinto produto sobra sozinho na segunda linha, com altura diferente dos demais.
- Botões "Adicionar ao pedido" e "Adicionar meia" empilhados em todos os cards, inclusive bebida (P1-04). A ação secundária tem o mesmo peso visual da principal.
- Filtros em uma linha só; no mobile, o quarto botão sai da tela (P1-06).
- Dois totais na mesma página; o segundo fica sempre `R$ 0,00` (P1-03).
- Preços sem moeda e com ponto decimal (P2-01).
- Dois frameworks CSS concorrentes (P1-07): botões, tipografia e espaçamento mudam de acordo com a ordem de carregamento.
- Contraste fraco nos botões coloridos (P2-06).
- Checkout quebra a identidade do cardápio: sem navbar, fonte monoespaçada, largura fixa de 80 mm centralizada em tela grande.
- Navbar vazia com um único botão vermelho grande, que é a ação mais destrutiva da tela (P3-04).
- `hover` com `scale(1.05)` no card inteiro causa deslocamento e não existe em toque (P3-08).

## 5. Impressão

### O que foi testado

- Chrome headless via CDP, com `Page.printToPDF` e `preferCSSPageSize=true`, no checkout com 2 itens.
- Resultado: 1 página, `612 × 792 pt` = **215,9 × 279,4 mm (Letter)**.
- Alvo: 80 mm de largura. Sem `@page`, o CSS `width: 80mm` só encolhe o conteúdo dentro de uma folha Letter.
- Captura do checkout mostra a nota centralizada, com campos e botões visíveis na tela; no papel, os botões são ocultados pelo `@media print`.

### Correção mínima

```css
@page {
  size: 80mm auto;
  margin: 0;
}
@media print {
  html, body { width: 80mm; margin: 0; }
  .btn-print { display: none; }
}
```

O MDN documenta `size` com comprimento (`size: 50mm 150mm`) e até dentro de `@media print`: <https://developer.mozilla.org/en-US/docs/Web/CSS/@page/size>.

### Bluetooth

O navegador não envia trabalho de impressão por Bluetooth. A Web Bluetooth API só acessa periféricos **BLE/GATT**, é experimental e não é Baseline: <https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API>. Impressoras térmicas de bancada normalmente usam Bluetooth Classic (SPP). O caminho correto é parear no Windows, instalar o driver e imprimir pelo diálogo do sistema, com a página em 80 mm. Se o driver não expuser a largura, o `@page` ainda define o tamanho lógico e o driver corta ou escala.

### O que falta na nota

- Número do pedido e status (entrega/retirada, pago/pendente).
- Forma de pagamento e troco.
- Telefone do cliente.
- Hora de saída e tempo estimado.
- Quebra de página segura para pedidos longos.

## 6. Arquitetura

Relatório visual: `C:\Users\wisla\AppData\Local\Temp\opencode\architecture-review-20261027.html`.

Candidatos, em ordem de força:

1. **Módulo de entrada de pedido (Strong).** Hoje o pedido vive em quatro lugares: objeto global, `localStorage`, texto do POST e string no banco. Uma interface `criar_pedido(itens, cliente)` concentra validação, preço e persistência. Fecha P0-01, P1-01 e P1-02 de uma vez.
2. **Catálogo e filtros (Strong).** Categoria aparece na view, no template e no CSS. Um `catalogo.filtrar(busca, categoria, pagina)` elimina a triplicação e ativa a paginação.
3. **Recibo de 80 mm (Strong).** Separar `recibo.html` e `recibo.css` do checkout dá à função principal uma interface testável: largura do PDF, conteúdo e quebra de página.
4. **Layout base e tokens (Worth exploring).** Um `base.html` e tokens únicos resolvem a mistura Bootstrap 4/5 e o visual em dois lugares.
5. **Estado do carrinho (Worth exploring).** Um módulo `Carrinho` com `adicionar`, `remover`, `total`, `serializar` elimina globais e IDs duplicados.

Recomendação: começar pelo intake. Sem ele, melhorar o visual só deixa o fluxo quebrado mais bonito.

## 7. Plano por fases

### Fase 0 — Segurança e higiene (S, 0,5 dia)

- Segredo fora do código; `DEBUG` por ambiente; `ALLOWED_HOSTS` explícito.
- Remover `.idea/`, `gunicorn-error-log`, `index.html.save` do índice.
- Corrigir README para refletir o que existe.
- **Aceite:** `manage.py check --deploy` sem `W009`/`W018`; `git ls-files` sem lixo.

### Fase 1 — Fechar o fluxo de pedido (M, 2-3 dias)

- Modelos `ItemPedido` (FK, produto, quantidade, preço unitário) e `Pedido` com status e timestamps.
- Formulário Django com CSRF; view POST com validação e redirect PRG.
- Total recalculado no servidor; nenhum preço vindo do cliente.
- Testes: POST válido, total adulterado, total vazio, produto inexistente.
- **Aceite:** pedido criado pela UI aparece no admin; `total=0.01` é rejeitado; `manage.py test` verde.

### Fase 2 — Impressão de 80 mm (M, 1-2 dias)

- `recibo.html` + `recibo.css` com `@page`.
- Número do pedido, pagamento, telefone e status na nota.
- Não limpar o carrinho antes da confirmação.
- Teste automatizado: PDF com largura de 80 mm e texto esperado.
- **Aceite:** PDF em 80 mm; impressão física confirmada pelo dono; cancelar não apaga o pedido.

### Fase 3 — Visual (M, 2-3 dias)

- `base.html`, tokens, navbar com marca.
- Corrigir IDs duplicados, condição da meia pizza e contraste.
- Grid responsivo e filtros com `flex-wrap`.
- **Aceite:** mobile 390 px sem overflow; um único total; nenhuma bebida com "meia"; contraste ≥ 4,5:1.

### Fase 4 — Catálogo (S, 1 dia)

- Paginação real, `page_obj` no template, links sem espaço.
- Busca e filtros preservados entre páginas.
- `Categoria` com choices ou modelo; `ordering`.
- **Aceite:** 5 produtos com página de 4 mostram 4 + 1; filtro sobrevive à paginação.

### Fase 5 — Robustez (S, 1 dia)

- Admin com `list_display`, busca e filtro.
- Logging, testes de regressão, remoção de código morto.
- **Aceite:** `manage.py test` cobre intake, catálogo e recibo; admin utilizável.

## 8. Evidências reproduzíveis

| Verificação | Comando | Resultado |
|---|---|---|
| Configuração | `manage.py check` | 0 issues |
| Deploy | `manage.py check --deploy` | 6 warnings (`W004`, `W008`, `W009`, `W012`, `W016`, `W018`) |
| Testes | `manage.py test` | 0 testes, `NO TESTS RAN` |
| Impressão | `Page.printToPDF` com `preferCSSPageSize=true` | 612 × 792 pt = 215,9 × 279,4 mm |
| Total adulterado | `Client.post('/checkout/', total='0.01')` | pedido salvo com total `0.01` |
| Total vazio | `Client.post('/checkout/', total='')` | `ValidationError` não tratado |
| Carrinho | 2 cliques em Margherita | `[2, "Margherita", 91.8]` |
| Meia pizza | 2 cliques em meia | `"Margherita / Calabresa"`, `47.9` |
| Importação | `python importar_produtos.py` | `ImproperlyConfigured` |

O servidor de teste usou banco em `%TEMP%` e settings temporário; o repositório não ganhou `db.sqlite3`. `git status` mostra `AUDITORIA.md` e `PROMPT-AUDITORIA.md` (este criado antes da auditoria, a pedido do usuário).

## 9. Não verificado

- **Impressão física** na térmica Bluetooth: exige o dispositivo e confirmação do dono.
- **Driver e pareamento do Windows:** não inspecionados; podem impor 80 mm independentemente do CSS.
- **`computer-use`:** runtime do Orca indisponível; teste feito com Chrome headless.
- **`understand` completo:** `pnpm` ausente; grafo de conhecimento não gerado.
- **Admin:** sem superusuário; fluxo de consulta não exercitado.
- **Firefox/Safari:** comportamento de `@page` e `window.print()` não testado.
- **Produção:** não há acesso ao host `34.39.141.209`; conclusões de segurança são estáticas.
