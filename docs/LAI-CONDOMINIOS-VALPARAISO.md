# Pedido de LAI — relação de condomínios de Valparaíso de Goiás

Use o e-SIC/protocolo da Prefeitura Municipal de Valparaíso de Goiás. Se não
houver e-SIC, protocole na Secretaria Municipal de Planejamento ou de Finanças.

## Texto do pedido

> **Assunto:** Pedido de acesso à informação — relação de condomínios
> residenciais do município
>
> Solicito, com base na Lei nº 12.527/2011 (Lei de Acesso à Informação), a
> relação dos condomínios residenciais e loteamentos fechados existentes no
> município de Valparaíso de Goiás/GO, incluindo, quando disponível:
>
> 1. denominação do condomínio ou empreendimento;
> 2. endereço completo (logradouro, número, bairro e CEP);
> 3. CNPJ do condomínio ou da associação de moradores, se houver;
> 4. situação do empreendimento (em funcionamento, em obras ou encerrado).
>
> Preferencialmente em formato aberto e editável (CSV, XLSX ou ODS), por meio
> de envio digital. Caso a informação esteja disponível em base pública,
> solicito a indicação do endereço eletrônico.
>
> Não solicito dados pessoais de moradores, síndicos ou responsáveis. O uso
> será operacional, para cadastro de endereços de entrega de uma pizzaria
> local.
>
> Coloco-me à disposição para esclarecimentos e informo que o pedido pode ser
> respondido por e-mail.

## Dados do requerente

Preencher com os dados da pizzaria:

```text
Nome/razão social:
CNPJ:
Endereço:
Telefone:
E-mail:
```

## Prazos e acompanhamento

- Prazo de resposta: 20 dias, prorrogável por mais 10 (art. 11 da Lei
  12.527/2011).
- Guarde o número de protocolo.
- Se a resposta vier em PDF, peça a planilha ou transcreva para
  `dados/condominios-prefeitura.csv` no mesmo schema do coletor.
- Se parte da informação for negada, peça a motivação e o trecho público.

## Encaixe no pipeline

O CSV da prefeitura entra como mais uma fonte:

```text
nome;endereco;numero;bairro;cidade;cep;referencia;ativo;revisado;fonte;nome_origem;cnpj
```

Use `fonte=prefeitura`, `revisado=nao` e siga a mesma revisão manual antes de
importar.
