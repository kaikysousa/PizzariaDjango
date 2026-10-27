# DESIGN.md — Pizzaria do Aislan

## Contexto das referências

Capturas feitas com Firecrawl em 27/10/2026:

- Domino's Brasil — `https://www.dominos.com.br/`
  - JSON: `.firecrawl/design-reference-1.json`
  - Screenshot: `.firecrawl/design-reference-1.png`
  - Extraído: primária `#FF0000`, secundária `#4B5563`, acento `#0090E2`, fundo `#FFFFFF`, botão pill `50px`, fontes Reddit Sans/Inter.
- Pizza Hut Brasil — `https://www.pizzahut.com.br/`
  - JSON: `.firecrawl/design-reference-2.json`
  - Extraído: primária `#E91C24`, texto `#1E1E1E`, fundo `#FFFFFF`, botão pill, base de espaçamento `8px`, Source Sans 3.

Padrões observados nas duas referências:

- vermelho como cor de ação;
- fundo branco com texto quase preto;
- botões em pílula;
- grade de produtos com CTA repetido;
- cabeçalho enxuto e hero de uma linha.

O que este projeto adota: pílula, CTA único por card, grade de produtos, cabeçalho enxuto, hierarquia clara.
O que este projeto recusa: fundo branco genérico, vermelho de marca alheia, tipografia sem personalidade e excesso de peso visual.
Não há uso de logo, imagem, fonte proprietária ou copy das referências.

## Direção

**Casa de bairro, acolhedora e direta.** Papel creme, tinta quente, vermelho de tomate e verde de manjericão. Títulos com serifa de personalidade; corpo com sans geométrica. O cardápio parece uma mesa posta, não um painel de fast-food.

## Tokens

| Token | Valor | Uso |
|---|---|---|
| `--fundo` | `#FAF6EF` | fundo geral |
| `--superficie` | `#FFFDF9` | cards, drawer, formulário |
| `--superficie-alt` | `#F3E9DB` | tags e chips neutros |
| `--tinta` | `#1F1A17` | texto principal |
| `--tinta-suave` | `#6B5E57` | texto secundário |
| `--primaria` | `#B33A1A` | CTA, preço, destaque |
| `--primaria-escura` | `#8F2D12` | hover e link |
| `--secundaria` | `#1F5A3D` | foco, passos, apoio |
| `--acento` | `#E9B44C` | badge, meia pizza, contador |
| `--borda` | `#E7DED2` | divisórias |
| `--erro` | `#A61B1B` | erro de formulário |
| `--raio` | `18px` | cards e blocos |
| `--raio-pill` | `999px` | botões e chips |
| `--container` | `1180px` | largura máxima |
| `--transicao` | `220ms cubic-bezier(.2,.7,.3,1)` | interações |

Contraste verificado: branco sobre `--primaria` = 6,07:1; `--primaria-escura` sobre `--fundo` > 7:1; `--tinta-suave` sobre `--fundo` > 5:1.

## Tipografia

- Títulos: **Fraunces**, peso 700, itálico para ênfase. Escala `h1 clamp(2.6rem, 6vw, 4.6rem)`, `h2 clamp(1.8rem, 3.4vw, 2.6rem)`, `h3 1.35rem`.
- Corpo: **DM Sans**, 400/500/600/700, 16px, linha 1.55.
- Rótulos: 0.75rem, caixa alta, `letter-spacing: .16em`.
- Recibo: Courier New 11px, para compatibilidade com térmica.

## Espaçamento e layout

- Base 4px; seções com `clamp(1.5rem, 3vw, 2.5rem)` de padding.
- Container 1180px.
- Grade de produtos: `repeat(auto-fill, minmax(240px, 1fr))`.
- Breakpoints: 900px (hero empilha, checkout empilha, nav esconde) e 640px (ações empilham, busca ocupa a linha).
- Alvos de toque mínimo 44×44.

## Componentes

- **Header:** sticky, fundo translúcido, marca com ícone de fatia, nav e botão de pedido com contador.
- **Hero:** título com itálico, apoio, dois CTAs, arte de pizza em CSS puro.
- **Chips:** filtro de categoria, ativo em vermelho.
- **Card de produto:** tag de categoria, preço, nome, descrição, CTA primário e "Meia" só para pizzas.
- **Aviso de meia:** faixa âmbar com a metade escolhida e cancelar.
- **Drawer do carrinho:** painel à direita, fundo escurecido, quantidade, remover, total e revisão.
- **Checkout:** resumo à esquerda, formulário à direita; erro por campo; nota de pagamento.
- **Recibo:** 80mm, `@page size: 80mm auto`, margem zero, botões fora da impressão.

## Motion

Três momentos, só com `transform` e `opacity`:

1. Entrada do cardápio: cards sobem 14px e aparecem em stagger de 55ms via `IntersectionObserver`.
2. Feedback do carrinho: contador pulsa 320ms e toast aparece por 2,6s.
3. Drawer: painel desliza da direita em 220ms; fundo escurece.

Guardrails:

- `prefers-reduced-motion: reduce` zera animações e transições.
- Nada de scroll-jacking, parallax, autoplay ou vídeo.
- Sem biblioteca de animação; orçamento de JS de motion < 30 KB gzip.
- Toque não depende de hover.

## Acessibilidade

- `lang="pt-BR"`, título e meta description por página.
- Skip link para `#conteudo`.
- Um `h1` por página e hierarquia `h2`/`h3` correta.
- Foco visível: `3px solid var(--secundaria)`.
- Contraste AA em texto, botões e chips.
- Labels explícitos em todos os campos.
- `aria-live` no contador e no toast.
- Drawer com `role="dialog"`, `aria-modal` e fechamento por Escape.
- Imagens decorativas com `aria-hidden`; não há imagens de produto.

## Evidências

- Antes: `%TEMP%\opencode\shots\before-390.png`, `before-768.png`, `before-1280.png`.
- Depois: `%TEMP%\opencode\shots\after-390.png`, `after-768.png`, `after-1280.png`.
- Probe: `scripts/ui_probe.py`.
- Lighthouse: `%TEMP%\opencode\lighthouse-before.json` e `lighthouse-after.json`.
