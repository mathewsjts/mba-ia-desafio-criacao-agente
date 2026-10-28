# 09: Chave e modelo Gemini configurados

**What to build:** o assistente responde mensagens reais com um modelo Gemini que a cota do projeto no Google AI Studio permite usar.

- O `.env` local tem a chave do Google AI Studio.
- Se o modelo padrão (`gemini-3.5-flash`) não estiver disponível ou tiver limite baixo demais para o fluxo do avaliador (algumas dezenas de chamadas), o `.env` define outro modelo em `AURORA_MODEL`.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `.env` criado a partir do `.env.example`, fora do Git, com `GOOGLE_API_KEY` preenchida
- [x] Modelo escolhido disponível na cota do projeto (padrão ou definido em `AURORA_MODEL`)
- [x] Com a API no ar, uma sessão nova recebe uma resposta real do modelo a uma mensagem simples, sem `503`

## Comments

- 2026-10-28: `.env` criado pelo usuário (ignorado pelo Git, confirmado com `git check-ignore .env`), com `GOOGLE_API_KEY` preenchida e `AURORA_MODEL=gemini-3.5-flash`. Com `uv run aurora-api` no ar, `POST /sessoes {"apartamento":"101"}` e depois `POST /sessoes/{id}/mensagens {"texto":"Olá, bom dia!"}` responderam `200 {"resposta":"Olá, bom dia! Como posso ajudar você hoje?","confirmacoes_pendentes":[]}`, sem `503`.
