# Auditoria complementar — Pizzaria Django

Data: 27/10/2026  
Base: commit `ea4b2d9`, branch `fix/auditoria-20261027`  
Método: Django 5.1.6, banco temporário com 6 produtos, Chrome headless via CDP em 390×844, 768×1024 e 1280×900, Lighthouse 12 mobile.

Esta auditoria cobre o que `AUDITORIA.md` não mediu: design, motion, acessibilidade, performance, SEO, estados de UX, segurança de runtime, dados, cross-browser e casos-limite de impressão.

## 1. Design baseline

- Não existe `base.html`: `index.html` e `checkout.html` repetem doctype, head e scripts. Cada mudança visual é feita duas vezes.
- Dois frameworks CSS concorrentes: Bootstrap 4.6.2 (`index.html:10`) e Bootswatch 5 Lux (`index.html:11`). O JS é Bootstrap 4 (`index.html:115`).
- Nenhum token: cores, raios, sombras e espaçamentos estão soltos em `static/css/estilos.css`.
- Sem hierarquia de headings: a página não tem `h1`, `h2` nem `h3`; usa `div.card-title` e `h5` (`index.html:45,73-74`).
- Navbar vazia com um único botão destrutivo (`index.html:21-25`).
- Dois totais na mesma tela (`index.html:45,103`); o segundo nunca atualiza.
- Preços sem moeda e com ponto decimal (`index.html:75`).
- Cardápio e checkout não compartilham identidade visual: checkout usa fonte monoespaçada e largura fixa de 80 mm (`checkout.html:8-14`).
- Grid fixo `col-md-3` (`index.html:70`): o quinto card sobra sozinho e os cards têm alturas diferentes.
- Estado de foco depende do Bootstrap; não há estilo próprio de `:focus-visible`.

## 2. Motion

- Único movimento: `transform: scale(1.05)` no hover do card (`estilos.css:73-75`). Causa deslocamento e não existe em toque.
- Nenhuma transição de entrada, feedback de carrinho, mudança de quantidade ou transição de checkout.
- Nenhum `@media (prefers-reduced-motion: reduce)` no CSS.
- Nenhum `IntersectionObserver` ou orçamento de animação.

## 3. Acessibilidade

Medições em 390 px, com 6 produtos:

| Problema | Evidência |
|---|---|
| Contraste abaixo de 4,5:1 | `ADICIONAR AO PEDIDO`: 1,63:1 (branco em `#ffc107`); `Filtrar: Pizzas Doces`: 2,85:1; `Filtrar: Pizzas`: 3,15:1; `Filtrar: Bebidas`: 3,15:1; `BUSCAR`: 3,13:1; `Remove a filtragem`: 3,81:1; `Página atual`: 3,98:1 |
| Alvos de toque pequenos | `BUSCAR` 84×40; `Página atual` 125×32 |
| Campo sem label | busca `item_name` |
| IDs duplicados | `pedido`, `total-pedido` e os IDs numéricos `1`–`6` |
| Idioma errado | `<html lang="en">` |
| Sem heading principal | nenhum `h1` |
| Sem link de pular navegação | ausente |

## 4. Performance

Lighthouse 12 mobile no baseline:

| Categoria | Score |
|---|---|
| Performance | 90 |
| Acessibilidade | 93 |
| Boas práticas | 96 |
| SEO | 90 |

Causas prováveis:
- 2 CSS de framework + 1 CSS local + jQuery + Popper + Bootstrap JS, todos de CDN e bloqueantes (`index.html:10-11,109-115`).
- Fonte padrão do sistema; nenhum preload.
- Sem imagens no cardápio, então o peso maior é CSS/JS.
- Nenhuma paginação real: todos os produtos são renderizados de uma vez.

## 5. SEO e metadados

- `<title>Title</title>` (`index.html:5`).
- Sem meta description, Open Graph, canonical ou dados estruturados de restaurante/cardápio.
- `lang="en"` em conteúdo português.
- Sem `robots.txt` ou `sitemap.xml`.
- Checkout tem `<title>Pedido - Pizzaria</title>` (`checkout.html:6`), melhor que o cardápio, mas ainda sem descrição.

## 6. Estados de UX

- Carrinho vazio mostra `R$ 0,00` e mantém "Fechar pedido" ativo (`index.html:44-49`).
- Não existe remover item nem alterar quantidade.
- Não existe estado de carregamento, erro de rede ou confirmação de sucesso.
- Cancelar a impressão limpa o carrinho (`checkout.html:153-159`).
- Não existe página de sucesso; o checkout é a própria nota.
- Meia pizza não mostra qual metade está pendente nem permite cancelar (`index.html:162-200`).

## 7. Segurança de runtime

- Nenhum form POST tem CSRF, porque o único POST possível não é enviado pela interface (`checkout.html:102`).
- Total e preço vêm do cliente (`checkout.html:143-149`); o servidor grava sem recalcular (`views.py:40-42`).
- Admin em `/admin/` sem restrição extra; depende do login do Django.
- `DEBUG=True` e `SECRET_KEY` versionada no baseline; corrigidos na Fase 1 desta branch.
- Sem headers de segurança no baseline; corrigidos na Fase 1.

## 8. Dados e migrações

- Nenhum `db.sqlite3` versionado; não há dados locais para migrar.
- `Pedido.items` é `CharField(3000)`; não há itens normalizados.
- `total` é `DecimalField`, mas recebe string do cliente.
- `Produto` sem `ordering`; paginação seria instável.
- Migração `0003` transformou `imagem` em `CharField(default=2)` e `0006` removeu o campo; histórico confuso.

## 9. Cross-browser

- Chrome: testado.
- Edge: mesmo motor Chromium; não testado nesta fase.
- Firefox: não instalado; não testado.
- Safari: indisponível no Windows.

## 10. Impressão

- PDF do checkout mede 215,9 × 279,4 mm (Letter), não 80 mm (`AUDITORIA.md`, seção 5).
- Não há `@page`.
- Nota longa não foi testada; não há quebra de página controlada.
- Campos novos (telefone, pagamento, status) não existem na nota.
- Número do pedido e token de acesso não existem.

## Evidências

- Capturas: `%TEMP%\opencode\shots\before-390.png`, `before-768.png`, `before-1280.png`.
- Probe JSON: `%TEMP%\opencode\probe-before.json`.
- Lighthouse: `%TEMP%\opencode\lighthouse-before.json`.
- Script: `scripts/ui_probe.py`.
