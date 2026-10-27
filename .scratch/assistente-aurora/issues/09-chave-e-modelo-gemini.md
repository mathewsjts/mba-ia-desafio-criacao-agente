# 09: Chave e modelo Gemini configurados

**What to build:** o assistente responde mensagens reais com um modelo Gemini que a cota do projeto no Google AI Studio permite usar.

- O `.env` local tem a chave do Google AI Studio.
- Se o modelo padrão (`gemini-3.5-flash`) não estiver disponível ou tiver limite baixo demais para o fluxo do avaliador (algumas dezenas de chamadas), o `.env` define outro modelo em `AURORA_MODEL`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [ ] `.env` criado a partir do `.env.example`, fora do Git, com `GOOGLE_API_KEY` preenchida
- [ ] Modelo escolhido disponível na cota do projeto (padrão ou definido em `AURORA_MODEL`)
- [ ] Com a API no ar, uma sessão nova recebe uma resposta real do modelo a uma mensagem simples, sem `503`
