# Correção da auditoria — Plano de implementação

> **Para agentes:** executar este plano tarefa por tarefa. Usar `test-driven-development`, `lean-build` e `unlazy`. Não pedir aprovação humana.

**Goal:** fechar todos os achados de `AUDITORIA.md`, auditar design/motion/acessibilidade/performance e entregar a branch `fix/auditoria-20261027` pronta para revisão.

**Architecture:** manter o app Django `pedidos`, normalizar pedido em `Pedido` + `ItemPedido`, centralizar criação em `pedidos/services.py`, separar recibo de checkout, adotar `base.html` + tokens CSS + JS nativo para motion.

**Tech Stack:** Django 5.1.6, SQLite (dev), HTML/CSS/JS nativo, Chrome headless para medições.

**Spec:** `AUDITORIA.md` + `PROMPT-CORRECAO.md`.

## Global Constraints

- Branch `fix/auditoria-20261027`; sem push, merge ou deploy.
- Textos de interface em português.
- Nenhum segredo, CNPJ, telefone ou dado fiscal inventado.
- `prefers-reduced-motion` respeitado; JS de motion ≤ 30 KB gzip.
- Commits em Conventional Commits, um por tarefa.

## Review Focus

- Pedido adulterado no cliente deve ser rejeitado no servidor.
- Cancelar a impressão não pode perder o carrinho.
- Carrinho vazio, quantidade zero e produto inexistente não podem gerar 500.
- Mobile em 390 px não pode ter overflow horizontal.
- Recibo longo não pode cortar item na quebra de página.

---

## Tarefa 1 — Higiene, segurança e scripts de gate

**Files:**
- Modify: `DjangoProject/settings.py`, `.gitignore`, `README.md`, `requirements.txt`
- Create: `.env.example`, `scripts/check_security.py`, `scripts/check_deploy.py`, `scripts/check_secrets.py`, `scripts/run_tests.py`, `requirements-dev.txt`
- Remove do índice: `.idea/`, `gunicorn-error-log`, `templates/pedidos/index.html.save`

**Interfaces:**
- Produz: `DEBUG` por `DJANGO_DEBUG`; `SECRET_KEY` por `DJANGO_SECRET_KEY`; `ALLOWED_HOSTS` por `DJANGO_ALLOWED_HOSTS`; `DJANGO_DB_PATH` opcional.

- [ ] Teste: `scripts/check_security.py` falha no código atual e passa depois.
- [ ] Implementar settings e `.env.example`.
- [ ] `git rm --cached` dos arquivos de IDE/log/backup; adicionar ao `.gitignore`.
- [ ] Reescrever README com estado real.
- [ ] Rodar os três scripts; esperar `GATE_* ok`.
- [ ] Commit `chore: protect settings and remove repo junk`.

## Tarefa 2 — Auditoria complementar

**Files:**
- Create: `AUDITORIA-COMPLEMENTAR.md`, `scripts/ui_probe.py`

**Interfaces:**
- Produz: achados com `arquivo:linha` ou medição para design, motion, a11y, performance, SEO, UX, segurança, dados, cross-browser e impressão.

- [ ] Subir servidor com banco temporário.
- [ ] Medir 390/768/1280 px com Chrome headless via CDP.
- [ ] Rodar Lighthouse mobile e registrar números.
- [ ] Registrar achados e adicionar gates faltantes ao `GATES.md`.
- [ ] Commit `docs: add complementary audit`.

## Tarefa 3 — Modelo de pedido e intake

**Files:**
- Modify: `pedidos/models.py`, `pedidos/admin.py`
- Create: `pedidos/services.py`, `pedidos/migrations/0008_pedido_normalizado.py`, `pedidos/tests/__init__.py`, `pedidos/tests/test_intake.py`
- Delete: `pedidos/tests.py`

**Interfaces:**
- `Categoria` choices: `pizza`, `pizza doce`, `bebida`.
- `Pedido`: `token` UUID, `status`, `pagamento`, `telefone`, `criado_em`, `atualizado_em`, `legacy_items`, `total`.
- `ItemPedido`: `pedido`, `produto`, `segundo_produto`, `quantidade`, `preco_unitario`, `subtotal`.
- `services.resolver_itens(itens: list[dict]) -> tuple[list[dict], Decimal]`
- `services.criar_pedido(*, itens, nome, telefone, endereco, endereco2, observacoes, pagamento) -> Pedido`

- [ ] Testes falhando: total recalculado, total adulterado ignorado, quantidade zero, produto inexistente, meia pizza, total vazio.
- [ ] Implementar modelos, migração e serviço.
- [ ] Rodar `test_intake`; verde.
- [ ] Migração reversível; dados legados em `legacy_items`.
- [ ] Commit `feat: add normalized order intake`.

## Tarefa 4 — Fluxo de checkout, URLs e recibo

**Files:**
- Modify: `pedidos/views.py`, `DjangoProject/urls.py`
- Create: `pedidos/forms.py`, `pedidos/tests/test_views.py`, `pedidos/tests/test_catalog.py`
- Create: `templates/pedidos/recibo.html`, `static/css/recibo.css`

**Interfaces:**
- `revisar_pedido(POST /carrinho/revisar/)`: valida JSON, grava sessão, redireciona `/checkout/`.
- `checkout(GET|POST /checkout/)`: GET renderiza resumo; POST cria e redireciona.
- `recibo(GET /pedido/<uuid:token>/recibo/)`: renderiza nota.
- `PedidoForm`: nome, telefone, endereco, endereco2, observacoes, pagamento.

- [ ] Testes: CSRF obrigatório, carrinho vazio redireciona, POST cria, form inválido 200, token errado 404.
- [ ] Implementar views, form e template de recibo com `@page { size: 80mm auto; margin: 0 }`.
- [ ] Recibo não limpa carrinho; botão "Novo pedido" limpa.
- [ ] Rodar `test_views` e `test_catalog`; verde.
- [ ] Commit `feat: add checkout flow and 80mm receipt`.

## Tarefa 5 — Design system, layout e motion

**Files:**
- Create: `templates/base.html`, `templates/pedidos/_card_produto.html`, `templates/pedidos/_carrinho.html`, `static/css/tokens.css`, `static/js/carrinho.js`, `static/js/motion.js`, `DESIGN.md`
- Modify: `templates/pedidos/index.html`, `templates/pedidos/checkout.html`, `static/css/estilos.css`
- Create: `scripts/check_ui.py`, `scripts/check_assets.py`

**Interfaces:**
- `tokens.css`: cores, espaço, tipografia, raio, sombra.
- `carrinho.js`: `Carrinho.adicionar(ids, nome, preco)`, `remover`, `alterarQtd`, `total`, `serializar`.
- `motion.js`: reveal com `IntersectionObserver`, feedback do carrinho, respeito a `prefers-reduced-motion`.

- [ ] `brainstorming` + referências + `firecrawl-website-design-clone` → `DESIGN.md`.
- [ ] `prototype` em `%TEMP%` em 390 e 1280 px.
- [ ] Implementar base, partials, tokens e JS.
- [ ] Corrigir IDs, meia pizza, preços pt-BR, contraste e overflow.
- [ ] Rodar `check_ui` e `check_assets`; verde.
- [ ] Commit `feat: redesign catalog with accessible motion`.

## Tarefa 6 — Catálogo e paginação

**Files:**
- Modify: `pedidos/views.py`, `templates/pedidos/index.html`
- Modify: `pedidos/tests/test_catalog.py`

- [ ] Testes: 4 por página + 1 restante; filtro sobrevive à página; busca combinada.
- [ ] Implementar `Paginator` com `page_obj` e links sem espaço.
- [ ] Commit `fix: restore catalog pagination and filters`.

## Tarefa 7 — Robustez e PDF

**Files:**
- Create: `pedidos/management/commands/seed_demo.py`, `scripts/check_receipt_pdf.py`, `scripts/check_print_js.py`, `pedidos/tests/test_robustness.py`
- Modify: `importar_produtos.py`, `DjangoProject/urls.py`, `pedidos/admin.py`

- [ ] Importação portátil com `django.setup()` e `--dry-run`.
- [ ] Rota de `MEDIA_URL` em DEBUG.
- [ ] Admin com `list_display`, busca e filtro.
- [ ] `seed_demo` cria produtos e pedido; PDF mede 80 mm.
- [ ] Rodar `test_robustness`, `check_receipt_pdf`, `check_print_js`; verde.
- [ ] Commit `fix: harden imports, media and admin`.

## Tarefa 8 — Verificação final

- [ ] `run_tests.py`: suíte inteira verde, > 0 testes.
- [ ] `check_deploy.py`: sem W009/W018.
- [ ] `check_security.py`, `check_secrets.py`, `check_ui.py`, `check_assets.py`: ok.
- [ ] Lighthouse mobile registrado.
- [ ] `requesting-code-review` + `caveman-review`.
- [ ] `RELATORIO-CORRECAO.md`.
- [ ] `GATES.md` sem gate aberto, exceto impressão física com `ABANDON`.
- [ ] Commit `docs: add correction report`.
