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

**Status:** resolved

- [x] Fase "antes" (passos 1–12) termina sem nenhuma falha
- [x] Fase "depois" (passos 13–14), após reinício real da API, termina sem nenhuma falha
- [x] Duas execuções completas consecutivas (restauração, antes, reinício, depois) passam, por causa do não determinismo do modelo
- [x] O log da API não tem o aviso de confirmação aprovada sem a ação executar
- [x] As referências de linha do README continuam corretas depois de qualquer mudança no código

## Comments

- 2026-10-28: tentativa bloqueada por cota do Gemini, sem nenhuma falha atribuível ao código ou às instruções. Duas execuções completas (`aurora-restaurar`, API no ar, `antes`, SIGINT na API e subida sem restaurar, `depois`):
  - Execução 1: 6 falhas no "antes" e 5 no "depois". Todas as falhas vêm de chamadas ao modelo que receberam `503 UNAVAILABLE` ("This model is currently experiencing high demand"), e a API respondeu `503` nessas mensagens (passos 3–6, 11, 12, 13 e 14). As verificações que não dependem do modelo passaram: confirmação negada não grava, aprovar grava exatamente uma reserva, reenvio e id inexistente recebem `409`, sessão inexistente recebe `404`, os eventos persistiram no reinício (53 eventos antes e depois) e as reservas e autorizações gravadas continuaram lá.
  - Execução 2: 15 falhas no "antes" e 9 no "depois". O log tem 34 `429 RESOURCE_EXHAUSTED` com `quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: 20`, `retryDelay: 31793s`. A chave está no plano gratuito, que permite 20 requisições por dia para `gemini-3.5-flash`, e uma execução completa do fluxo faz bem mais que 20 chamadas (cada mensagem chama o agente principal e o especialista, às vezes várias vezes).
  - O aviso "Confirmação … aprovada, mas a ação não executou." não apareceu em nenhum dos dois logs.
  - Nenhum código foi alterado. Os critérios continuam desmarcados: não é possível chegar a duas execuções consecutivas sem falha com essa cota. Para seguir é preciso uma chave com faturamento ativo (ou com cota diária maior) ou um `AURORA_MODEL` cuja cota gratuita comporte o fluxo, e depois rodar o fluxo de novo.
- 2026-10-28: com faturamento ativo no projeto, o fluxo passou. Três execuções completas (`aurora-restaurar`, API no ar, `antes`, SIGINT na API e subida sem restaurar, `depois`), cada uma com 50 verificações `ok`, 0 `FALHA` e "Tudo certo." nas duas fases. Os logs da API não têm nenhuma resposta 5xx, nenhum `503 UNAVAILABLE` ou `429 RESOURCE_EXHAUSTED` e nenhum aviso "Confirmação … aprovada, mas a ação não executou.". Os eventos de S1 persistiram no reinício (62 antes e 62 depois). Não foi preciso nenhum retry no cliente do modelo.
  - Execução 3 (código como estava): passou, mas as respostas depois das aprovações estavam erradas. No passo 8 o especialista recebeu `{"status": "reservada", "cobranca": true, "taxa": 150.0}` e respondeu que a reserva "ficará pendente de aprovação no seu aplicativo". No passo 11 o agente principal disse que "a aprovação final deve ser feita diretamente pela tela do aplicativo". A ação já tinha executado nos dois casos, então nenhuma garantia foi violada; o problema era o texto mentir para o morador. O modelo misturava a docstring de `reservar_area` ("ficam pendentes até o morador aprovar") e a regra do agente principal sobre aprovação no chat com um resultado que já tinha vindo depois da aprovação.
  - Correção apenas nas instruções (uma regra nova em cada um dos três agentes): `status` `reservada` ou `autorizada` quer dizer que a aprovação pelo aplicativo já aconteceu, então a resposta não pode dizer que ainda falta aprovar. Nenhuma tool nem verificação de código mudou. As referências de linha do README para `FunctionTool(..., require_confirmation=...)` foram atualizadas (`reservas.py` 127→129 e `visitantes.py` 80→82); as outras referências continuam apontando para as mesmas linhas.
  - Execuções 4 e 5 (código final, consecutivas): sem falhas. Respostas à aprovação do passo 8: "O Salão de Festas foi reservado com sucesso para o dia 20/04/2030!" e "O salão de festas foi reservado com sucesso … Código da reserva: RSV-I8MDXG, Taxa: R$ 150,00". Não apareceu nenhuma resposta dizendo que houve uma "falha temporária".
