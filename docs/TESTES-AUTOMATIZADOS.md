# Testes automatizados

## Suíte E2E de gestão

`pedidos/tests/test_e2e_gestao.py` cobre o fluxo completo junto: cardápio,
carrinho, checkout, aprovação da loja, estoque, painel e recibo.

Os testes usam `django.test.TestCase` e o banco de teste do Django. Não há
sleep, acesso à rede, banco real nem dependência de ordem de execução. Os dados
mínimos (usuários, produtos, ingredientes, fichas e condomínio) nascem no
`setUp` de cada teste.

### Cenários cobertos

1. Checkout de cliente com condomínio: pedido nasce `aguardando_aprovacao`,
   endereço é preenchido pelo condomínio e o estoque não muda.
2. Aprovação pelo painel: status `aprovado`, baixa de estoque, movimento de
   saída e recibo liberado.
3. Meia pizza: consumo de metade da ficha de cada sabor, preço médio e total.
4. Cancelamento após aprovação: estorno único do estoque e motivo visível no
   painel e no acompanhamento.
5. Pedido manual de balcão: nasce `aprovado`, baixa estoque e calcula o total.
6. Edição de itens aprovados: estorno e reaplicação sem duplicar movimentos.
7. Bloqueio após `preparando`: itens em leitura, mas nome, observação e status
   continuam editáveis.
8. Estoque abaixo do mínimo: aprovação derruba o saldo e o alerta aparece no
   dashboard e na lista de estoque.
9. Fluxo de status: `aprovado -> preparando -> saiu -> entregue` e rejeição de
   transições inválidas.
10. Segurança: painel restrito a staff, ações bloqueadas para usuário comum,
    isolamento por token e CSRF nos POSTs.

### Comandos

```bash
python manage.py test
python manage.py test pedidos.tests.test_e2e_gestao
python manage.py makemigrations --check --dry-run
python manage.py check
ruff check .
```

### Leitura dos resultados

- Todos os testes devem passar sem `skip`.
- `makemigrations --check --dry-run` deve responder `No changes detected`.
- `check` e `ruff check .` não devem apontar problemas.
