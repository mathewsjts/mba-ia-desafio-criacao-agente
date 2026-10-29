# Confirmação nativa do ADK 2.13.0 e topologia dos agentes

Ações que geram cobrança ou criam autorização de visita usam a confirmação de tools nativa do ADK (`FunctionTool(require_confirmation=...)`). A rota `/confirmacoes` devolve ao Runner um `FunctionResponse` `adk_request_confirmation` com `{"confirmed": bool}`. Fixamos `google-adk[db]==2.13.0` porque, a partir dela, o Runner encaminha a resposta da confirmação ao agente que a pediu (`_session_for_routing`). Na 2.9.1, a resposta podia cair em outro agente e ser ignorada em silêncio, e o reenvio de uma resposta já dada executava a tool de novo.

A topologia é um agente principal em modo chat, sem tools de domínio, com dois especialistas `reservas` e `visitantes` como sub-agents `mode="single_turn"`, donos das tools que pedem confirmação. Há também um especialista `regulamento` exposto como `AgentTool`, cuja execução interna roda numa sessão descartável e não grava trechos do regulamento nos eventos da sessão.

## Considered Options

- **Tabela própria de ações pendentes, executadas pela rota sem o modelo**: mais simples e robusta, mas contorna o mecanismo de confirmação que o desafio pede para dominar. Descartada depois de a confirmação nativa passar com sessão SQLite persistida, inclusive com reinício entre o pedido e a aprovação.
- **Especialistas de ação como `AgentTool`**: a confirmação nunca chega ao cliente, porque o `AgentTool` roda numa sessão em memória que não pode ser retomada.
- **Tools de confirmação no agente principal**: a única forma que funciona também na 2.9.1, mas esvazia os especialistas.

## Consequences

- A API mantém sua própria checagem de 409: as confirmações pendentes são as chamadas `adk_request_confirmation` sem resposta com o mesmo id nos eventos da sessão. Ela não confia na deduplicação do ADK.
- Duas requisições simultâneas na mesma sessão geram `StaleSessionError`, então a API serializa as requisições por sessão com um lock.
- Atualizar o ADK exige repetir os testes de confirmação com sessão persistida e reinício, porque o roteamento da retomada mudou entre versões.
