# 03 Sessões persistidas e rotas de conversa

Status: ready-for-agent
Blocked by: 02

Ver `../spec.md` (Sessão e apartamento, API).

## O que fazer

- `DatabaseSessionService` em `var/sessoes.db`, `Runner` e `App` montados em `agentes/__init__.py`. Nesta issue, só o agente principal, sem especialistas.
- `POST /sessoes`: `422` para apartamento inexistente, `state={"apartamento"}`, responde `201`.
- `POST /sessoes/{id}/mensagens`: monta `resposta` a partir dos eventos finais da invocação. `confirmacoes_pendentes` fica vazio por enquanto.
- `GET /sessoes/{id}/eventos`: dump completo, em ordem.
- `404` para sessão inexistente em todas as rotas com `{session_id}`.
- Lock por sessão.
- Erros do modelo viram `503`.

## Aceite

- Passos 2 e 9b (`GET /sessoes/sessao-inexistente/eventos` → `404`).
- Depois de reiniciar a API, `GET /eventos` devolve a mesma quantidade de eventos, e uma nova mensagem funciona (parte do passo 13).
