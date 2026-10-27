# Relatório de correção — Pizzaria Django

Data: 27/10/2026  
Branch: `fix/auditoria-20261027`  
Base: `main` (`ea4b2d9`)

## Resultado

- 15 gates cumpridos, 1 abandonado (impressão física).
- 48 testes automatizados, 0 falhas.
- PDF do recibo: **80,1 mm** de largura, 1 página.
- Lighthouse mobile: **performance 99**, **acessibilidade 100**, **SEO 100**, **CLS 0**.
- `manage.py check --deploy`: sem `W009` e `W018`.
- Nenhum segredo versionado.

## Achados fechados

### P0

| ID | Status | Evidência |
|---|---|---|
| P0-01 checkout não persistia | fechado | POST com CSRF, token de idempotência e redirect para recibo; `test_views` |
| P0-02 recibo não tinha 80 mm | fechado | `@page` + PDF medido em 80,1 mm; `check_receipt_pdf.py` |
| P0-03 segredo, DEBUG e IP pública | fechado | settings por ambiente, `.env.example`, `check_security.py` |

### P1

| ID | Status | Evidência |
|---|---|---|
| P1-01 total confiado ao cliente | fechado | `services.resolver_itens` recalcula tudo; teste de total adulterado |
| P1-02 total vazio gerava 500 | fechado | validação de formulário e serviço; testes de entrada inválida |
| P1-03 IDs duplicados | fechado | `check_ui.py` e teste de HTML |
| P1-04 meia pizza em bebidas | fechado | condição por categoria; teste de catálogo |
| P1-05 paginação morta | fechado | `Paginator` real, `page_obj`, links com `{% querystring %}`; `test_catalog` |
| P1-06 filtros estouravam no mobile | fechado | chips com `flex-wrap`; probe em 390 px sem overflow |
| P1-07 Bootstrap 4 + Bootswatch 5 | fechado | CSS próprio, sem frameworks concorrentes |
| P1-08 cancelar impressão apagava carrinho | fechado | recibo não limpa sozinho; botão "Novo pedido"; `check_print_js.py` |
| P1-09 zero testes | fechado | 48 testes |

### P2 e P3

- Preços em pt-BR, `Decimal` e `R$` em cardápio, checkout e recibo.
- Importação CSV portátil, com `django.setup()`, `--dry-run`, validação de categoria e preço.
- `MEDIA_URL` com rota em DEBUG.
- README reescrito e aderente ao código.
- `Produto` com `ordering` explícito, índice e `disponivel`.
- Contraste AA em botões, chips e textos; foco visível; alvos ≥ 44 px.
- `lang="pt-BR"`, title e meta description por página; JSON-LD de restaurante.
- `.idea/`, `gunicorn-error-log` e `index.html.save` fora do índice.
- Admin com lista, busca, filtros e inline somente leitura.
- Código morto removido; imports duplicados eliminados.
- CTAs, filtros e paginação com URLs corretas.

## Auditoria complementar

Fechados:

- design system com `DESIGN.md`, tokens e base compartilhada;
- motion com `IntersectionObserver`, três momentos e `prefers-reduced-motion`;
- acessibilidade: contraste, foco, labels, um `h1`, skip link, drawer `<dialog>`;
- responsividade em 390, 768 e 1280 px sem overflow;
- SEO: metadados, Open Graph, JSON-LD, `noindex` no recibo;
- estados de UX: carrinho vazio, erro de formulário, meia pizza visível, recibo longo;
- segurança de runtime: CSRF, token de idempotência, recibo por UUID com `no-store`;
- dados: migração reversível, legado preservado em `legacy_items`.

## Revisão de código

Revisor independente apontou 4 críticos e 8 importantes. Corrigidos:

1. JSON não-objeto causava 500 no checkout.
2. Quantidade sem limite causava `InvalidOperation`.
3. `[hidden]` era sobrescrito por `display:flex`, mostrando banner e contador falsos.
4. Recibo com altura fixa, margem de impressão e risco de corte entre itens.
5. Mensagens e erros de formulário sem anúncio/foco.
6. Drawer sem focus trap; alvos de 34 px.
7. Contador do carrinho zerado no checkout.
8. Recibo indexável e cacheável.
9. Importação aceitava categoria/preço inválidos.
10. Duplo submit criava dois pedidos.

Também foram feitos: `python-dotenv`, WhiteNoise, Django 5.2.18 LTS, HSTS de 1 ano e CNPJ opcional por ambiente.

## Gates

`GATES.md` reporta **15 cumpridos, 1 abandonado**:

- `G14` — impressão física. Não há impressora nem dono presentes. PDF de 80,1 mm gerado, CSS documentado e procedimento abaixo.

Para repetir:

```bash
.venv\Scripts\python.exe scripts\run_tests.py
.venv\Scripts\python.exe scripts\check_ui.py
.venv\Scripts\python.exe scripts\check_receipt_pdf.py
node ~/.agents/skills/unlazy/scripts/gate-check.mjs GATES.md
```

## Impressão física — pendência do dono

1. Pareie a impressora de 80 mm no Windows e instale o driver.
2. Rode a aplicação e crie um pedido.
3. Abra o recibo e clique em **Imprimir**.
4. Selecione a impressora e papel de 80 mm.
5. Confirme que a largura, a margem e o corte estão corretos.

O navegador não envia trabalho por Bluetooth. O pareamento e o driver são do sistema operacional.

## Não verificado

- Impressão física e corte na térmica.
- Firefox/Safari e zoom 200%.
- Deploy real no host de produção.
- Volume real de pedidos e dados existentes.
- Pagamento online e documento fiscal.

## Evidências

- Auditoria: `AUDITORIA.md`
- Auditoria complementar: `AUDITORIA-COMPLEMENTAR.md`
- Design: `DESIGN.md`
- Plano: `docs/superpowers/plans/2026-10-27-correcao-auditoria.md`
- Capturas antes/depois: `%TEMP%\opencode\shots`
- Lighthouse: `%TEMP%\opencode\lighthouse-before.json` e `lighthouse-after.json`
- PDF: `%TEMP%\opencode\gate-receipt.pdf`
