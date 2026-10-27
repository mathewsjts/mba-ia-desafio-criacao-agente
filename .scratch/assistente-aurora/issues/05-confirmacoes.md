# 05 Confirmação de cobrança pela rota de confirmações

Status: ready-for-agent
Blocked by: 04

Ver `../spec.md` (Confirmações), ADR 0001.

## O que fazer

- `reservar_area` como `FunctionTool(..., require_confirmation=lambda area, data: taxa(area) > 0)`. Remover o bloqueio provisório da issue 04.
- `confirmacoes.py`:
  - Extrair as pendentes dos eventos (`id`, `acao`, `detalhes`).
  - Montar o `FunctionResponse` `adk_request_confirmation`.
  - Conferir depois da retomada que a tool executou de fato, com warning no log se não executou.
- `POST /sessoes/{id}/confirmacoes`: `409` se o id não está pendente, checado dentro do lock. Senão, retoma o Runner.
- Preencher `confirmacoes_pendentes` nas duas rotas.
- `POST /mensagens` com pendência: responde `200` sem chamar o modelo.

## Aceite

- Passo 7: pendência com área e data em `detalhes`; nada gravado; negar mantém tudo igual.
- Passo 8: aprovar grava exatamente uma reserva; reenviar o mesmo id dá `409` e não muda nada.
- Passo 9a: `id-inexistente` dá `409`.
- Passo 10: em S2, o salão em 2030-03-16 não é reservado, sem `RSV-4821` e sem o número 302 isolado nas respostas e nos eventos.
- Passo 14: duas aprovações simultâneas em S3 e S4 respondem `200`, e a soma é exatamente uma reserva.
- A aprovação funciona também depois de reiniciar a API entre o pedido e a aprovação.
