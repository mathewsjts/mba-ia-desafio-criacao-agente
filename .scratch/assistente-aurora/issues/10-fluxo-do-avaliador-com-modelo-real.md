# 10: Fluxo do avaliador passando com o modelo real

**What to build:** os passos 1–14 do fluxo do avaliador (`docs/enunciado.md`) passam com o modelo Gemini real.

- Usar o script do fluxo do avaliador:
  1. Restaurar os dados e subir a API.
  2. Rodar a fase "antes" (passos 1–12).
  3. Parar a API com Ctrl+C e subir de novo, sem restaurar.
  4. Rodar a fase "depois" (passos 13–14).
- Falhas vindas do comportamento do modelo (roteamento errado, resposta sem o horário da piscina, número 302 isolado numa resposta, ação anunciada sem a tool ter executado) são corrigidas nas instruções dos agentes ou nas tools.
- A correção nunca afrouxa uma garantia: confirmação, apartamento da sessão, persistência, regulamento por capítulo e exclusividade na gravação continuam no código (ver ADR 0001 e ADR 0002).
- Se aparecer o aviso de confirmação aprovada sem a ação executar, o problema está no roteamento da retomada e precisa ser investigado antes de qualquer ajuste de prompt.

**Blocked by:** 09 (Chave e modelo Gemini configurados)

**Status:** ready-for-agent

- [ ] Fase "antes" (passos 1–12) termina sem nenhuma falha
- [ ] Fase "depois" (passos 13–14), após reinício real da API, termina sem nenhuma falha
- [ ] Duas execuções completas consecutivas (restauração, antes, reinício, depois) passam, por causa do não determinismo do modelo
- [ ] O log da API não tem o aviso de confirmação aprovada sem a ação executar
- [ ] As referências de linha do README continuam corretas depois de qualquer mudança no código
