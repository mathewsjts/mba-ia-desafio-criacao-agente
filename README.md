# Regra é regra: o assistente virtual do Residencial Aurora

Assistente do aplicativo dos moradores do Residencial Aurora, feito com Google ADK e exposto por uma API FastAPI em `http://localhost:8000`. Pelo chat, o morador reserva o salão de festas, a churrasqueira e a quadra, cancela as próprias reservas, autoriza visitantes e tira dúvidas sobre o regulamento interno.

A filosofia é a do desafio: **o modelo decide o caminho, o código decide o que é permitido**. Cada regra crítica está numa tool, numa constraint do banco ou na API. Nenhuma depende do que o modelo escreve.

- Enunciado completo: [docs/enunciado.md](docs/enunciado.md)
- Vocabulário do domínio: [GLOSSARY.md](GLOSSARY.md)
- Decisões de arquitetura: [docs/adr/](docs/adr/)

## Arquitetura

```
POST /sessoes/{id}/mensagens ─┐
POST /sessoes/{id}/confirmacoes ─┤  api.py (FastAPI + Runner do ADK, lock por sessão)
                                 ▼
              assistente_aurora (agente principal, modo chat, sem tools de domínio)
               ├── reservas    (sub-agent, mode="single_turn")  → tools de reserva
               ├── visitantes  (sub-agent, mode="single_turn")  → tools de autorização de visita
               └── regulamento (AgentTool)                      → ler_capitulo
                                 │
          var/condominio.db (reservas, autorizações)   var/sessoes.db (sessões e eventos do ADK)
```

| Agente | Responsabilidade | Como é acionado | Por quê |
|---|---|---|---|
| `assistente_aurora` ([agentes/\_\_init\_\_.py](src/aurora/agentes/__init__.py)) | Conversa com o morador e encaminha cada pedido ao especialista certo. Não lê nem grava dados e não recebe o regulamento nas instruções. | Raiz do `App`, chamado pelo `Runner` a cada mensagem. | Mantém o contexto principal pequeno e sem acesso direto a dados. |
| `reservas` ([agentes/reservas.py](src/aurora/agentes/reservas.py)) | Lista as reservas do apartamento, verifica disponibilidade, reserva e cancela. | Sub-agent `mode="single_turn"`: o principal o chama como tool, ele executa a tarefa e devolve o resultado. | A tool `reservar_area` pede confirmação. O sub-agent roda dentro da sessão persistida, então a execução pausa e é retomada nele quando a rota de confirmações responde. Um `AgentTool` não consegue retomar ([ADR 0001](docs/adr/0001-confirmacao-nativa-do-adk-e-topologia-dos-agentes.md)). |
| `visitantes` ([agentes/visitantes.py](src/aurora/agentes/visitantes.py)) | Lista e cria autorizações de visita. | Sub-agent `mode="single_turn"`, como o de reservas. | Mesmo motivo: `autorizar_visitante` pede confirmação para toda autorização nova. |
| `regulamento` ([agentes/regulamento.py](src/aurora/agentes/regulamento.py)) | Responde dúvidas lendo um capítulo do regulamento por vez. | `AgentTool` no agente principal. | O `AgentTool` roda o especialista numa sessão descartável: o capítulo lido nunca entra nos eventos da sessão do morador, só a resposta final. |

Escolhas de suporte:

- **ADK `google-adk[db]==2.13.0`**. A partir dessa versão, o Runner encaminha a resposta de uma confirmação ao agente que a pediu, qualquer que seja a topologia. Nas versões anteriores, a resposta podia cair em outro agente e ser ignorada em silêncio.
- **Modelo:** um único modelo Gemini para todos os agentes, configurável em `AURORA_MODEL` (padrão `gemini-3.5-flash`).
- **Armazenamento:** SQLite, sem serviço externo ([ADR 0002](docs/adr/0002-sqlite-com-indice-unico-parcial.md)). As sessões ficam no `DatabaseSessionService` do ADK, em `var/sessoes.db`, e os dados do condomínio em `var/condominio.db`. Os arquivos de `dados/` só são lidos, nunca alterados.

## Garantias

### 1. Cobrança ou autorização de visita só com confirmação

- **Quem decide se pede confirmação é o código, não o modelo.**
  - [agentes/reservas.py:43](src/aurora/agentes/reservas.py#L43) `_gera_cobranca`, ligado em `FunctionTool(reservar_area, require_confirmation=_gera_cobranca)` ([linha 140](src/aurora/agentes/reservas.py#L140)). Pede confirmação quando a área existe, tem `taxa > 0`, a data é válida e a área está livre nessa data. Área sem taxa não pede confirmação.
  - [agentes/visitantes.py:26](src/aurora/agentes/visitantes.py#L26) `_autoriza_visita`, ligado em `FunctionTool(autorizar_visitante, require_confirmation=_autoriza_visita)` ([linha 95](src/aurora/agentes/visitantes.py#L95)). Pede confirmação para toda autorização nova: data válida e sem autorização com o mesmo nome e data para o apartamento.
  - Quando a função devolve verdadeiro, o ADK não executa o corpo da tool: ele registra uma chamada `adk_request_confirmation` e pausa. O corpo só roda depois que essa chamada recebe resposta, e a resposta negada não o executa. O ADK reavalia a função na retomada.
- **Negar encerra o pedido.** O `before_tool_callback` [agentes/\_comum.py:25](src/aurora/agentes/_comum.py#L25) `respeitar_negacao`, dos dois especialistas, roda antes do pedido de confirmação do ADK. Depois que o morador nega, ele responde `negada` à tool negada até o fim daquele pedido ([confirmacoes.py:51](src/aurora/confirmacoes.py#L51) `negadas_na_invocacao`), sem executá-la e sem abrir outra confirmação, mesmo que o modelo tente de novo. Ele só recusa, nunca aprova. Um novo pedido do morador volta a pedir confirmação.
- **Quando não se pede confirmação, o corpo da tool não grava sem aprovação.** Se a função devolve falso, o corpo roda direto. Isso acontece com área ou data inválida (a tool responde `invalido`), com área com taxa já ocupada na data, com autorização duplicada, ou quando a situação muda entre o pedido e a retomada. Nesses casos:
  - [reservas.py:70](src/aurora/agentes/reservas.py#L70): `reservar_area` em área com taxa e sem aprovação responde `indisponivel` sem gravar.
  - [visitantes.py:49](src/aurora/agentes/visitantes.py#L49): `autorizar_visitante` sem aprovação responde `ja_autorizada` sem gravar.
  - A aprovação é lida por [agentes/\_comum.py:18](src/aurora/agentes/_comum.py#L18) `aprovada_pelo_morador`, de `tool_context.tool_confirmation`. Esse campo só é preenchido pelo ADK a partir da resposta à chamada `adk_request_confirmation`, que só a rota de confirmações envia. O modelo não tem como escrever nele, então essa checagem não depende do que o modelo decide chamar nem do que o morador escreve no chat.
- **A confirmação vem do sistema, não da conversa.**
  - [confirmacoes.py:31](src/aurora/confirmacoes.py#L31) `pendentes` lê dos eventos da sessão as chamadas `adk_request_confirmation` ainda sem resposta.
  - A rota [api.py:131-146](src/aurora/api.py#L131-L146) só aceita um `id` dessa lista. Qualquer outro id, inclusive um já respondido, recebe `409` antes de chegar ao Runner, então aprovar executa uma única vez.
  - Com uma confirmação pendente, uma nova mensagem nem chama o modelo ([api.py:123](src/aurora/api.py#L123)), então "já estou confirmando aqui" não aprova nada.
- **Verificação depois de aprovar.** [confirmacoes.py:71](src/aurora/confirmacoes.py#L71) `acao_executada` confere que a tool aprovada rodou de fato e registra um aviso se não rodou.

### 2. Cada sessão pertence a um apartamento

- **O apartamento é gravado uma única vez**, no state da sessão, na criação ([api.py:114](src/aurora/api.py#L114)). Apartamento inexistente recebe `422`.
- **Nenhuma tool recebe apartamento como parâmetro.** Todas o leem do state por [agentes/\_comum.py:13](src/aurora/agentes/_comum.py#L13) `apartamento_da_sessao`, e o modelo não tem como escrever no state.
- **As consultas e gravações filtram pelo apartamento** ([condominio.py:111](src/aurora/condominio.py#L111) `listar_reservas`, [condominio.py:159](src/aurora/condominio.py#L159) `cancelar`, autorizações idem). Cancelar a reserva de outro apartamento devolve "você não tem reserva dessa área nessa data".
- **A disponibilidade não revela o dono.** Ela é consultada por [condominio.py:122](src/aurora/condominio.py#L122) `area_livre`, que devolve só livre ou ocupada. Reservar uma data ocupada devolve só `indisponivel`, então nenhum código, nome ou número de outro apartamento chega à conversa.

### 3. Nada se perde no reinício

- **Sessões e eventos** ficam no `DatabaseSessionService` em SQLite ([api.py:38](src/aurora/api.py#L38)).
- **Reservas e autorizações** ficam em `var/condominio.db`.
- **Subir a API não reseta nada.** O startup só cria o banco se ele não existir ([condominio.py:83](src/aurora/condominio.py#L83) `garantir_banco`); só `aurora-restaurar` volta ao estado inicial.
- **Confirmações sobrevivem ao reinício.** Uma confirmação pendente antes do reinício pode ser aprovada depois, porque as confirmações pendentes são lidas dos eventos persistidos.
- **Nenhum código de reserva se repete.** Cancelar muda o status para `cancelada` em vez de apagar, então a chave primária em `codigo` cobre também os códigos de reservas canceladas.

### 4. O regulamento é consultado, não carregado

- **O agente principal não recebe o regulamento.** A instrução dele ([agentes/\_\_init\_\_.py:13](src/aurora/agentes/__init__.py#L13)) só diz para encaminhar dúvidas ao especialista.
- **O especialista lê um capítulo por vez.** A instrução dele traz apenas o índice de capítulos, e [agentes/regulamento.py:14](src/aurora/agentes/regulamento.py#L14) `ler_capitulo` devolve um único capítulo. Cada capítulo trata de um único assunto ([regulamento.py](src/aurora/regulamento.py)).
- **O texto do capítulo não entra na sessão.** O especialista é um `AgentTool` ([agentes/regulamento.py:45](src/aurora/agentes/regulamento.py#L45)), que roda numa sessão em memória descartável. Só a resposta final volta aos eventos da sessão do morador.

### 5. Dois moradores, uma reserva

- **A exclusividade vale no instante da gravação.** Ela é garantida pelo índice único parcial [condominio.py:33](src/aurora/condominio.py#L33): `CREATE UNIQUE INDEX reserva_ativa_unica ON reservas(area, data) WHERE status = 'ativa'`.
- **A segunda gravação é recusada sem erro de servidor.** Quando duas aprovações chegam ao mesmo tempo, as duas podem ter visto a data livre, mas o SQLite serializa as escritas e o segundo `INSERT` falha com `IntegrityError`. [condominio.py:136-156](src/aurora/condominio.py#L136-L156) `reservar` o traduz em `None`, e a tool responde `indisponivel` normalmente, com `200`.
- **Requisições na mesma sessão não colidem.** Um `asyncio.Lock` por sessão ([api.py:121](src/aurora/api.py#L121), [api.py:133](src/aurora/api.py#L133)) evita que duas requisições simultâneas na mesma sessão gravem eventos concorrentes.

## Como rodar

### Pré-requisitos

- [uv](https://docs.astral.sh/uv/). Ele instala o Python 3.13 fixado em `.python-version`, se for preciso.
- Uma chave do [Google AI Studio](https://aistudio.google.com/apikey).
- `curl` e `jq`, só para o script do fluxo do avaliador.

### Variáveis do `.env`

```bash
cp .env.example .env
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `GOOGLE_API_KEY` | sim | Chave do Google AI Studio. |
| `GOOGLE_GENAI_USE_VERTEXAI` | não | Deixe vazio para usar a API do Google AI Studio (padrão). `TRUE` usaria a Vertex AI, que este projeto não usa. |
| `AURORA_MODEL` | não | Modelo Gemini usado por todos os agentes. Padrão: `gemini-3.5-flash`. |

### Comandos

```bash
uv sync                 # instala as dependências (google-adk[db]==2.13.0 fixado)
uv run aurora-restaurar # volta reservas e autorizações de visita ao estado de dados/ e apaga as sessões
uv run aurora-api       # sobe a API em http://localhost:8000
```

- **Restauração:** rode `aurora-restaurar` com a API parada. Ele recria `var/condominio.db` a partir de `dados/*.json` e apaga `var/sessoes.db`, para que nenhuma confirmação antiga seja aprovada sobre os dados restaurados.
- **Sem restaurar:** a API também sobe direto. Se o banco não existir, ela o cria com os dados iniciais.

### Fluxo do avaliador

[scripts/fluxo_avaliador.sh](scripts/fluxo_avaliador.sh) reproduz os passos 1 a 14 do enunciado com `curl` e confere cada verificação:

```bash
uv run aurora-restaurar && uv run aurora-api   # terminal 1
scripts/fluxo_avaliador.sh antes               # terminal 2: passos 1 a 12
# Ctrl+C no terminal 1 e uv run aurora-api de novo
scripts/fluxo_avaliador.sh depois              # terminal 2: passos 13 e 14
```

### API

| Rota | Resposta |
|---|---|
| `POST /sessoes` `{"apartamento"}` | `201 {"session_id"}`; `422` se o apartamento não existe |
| `POST /sessoes/{id}/mensagens` `{"texto"}` | `200 {"resposta", "confirmacoes_pendentes"}` |
| `POST /sessoes/{id}/confirmacoes` `{"id", "confirmado"}` | `200` no mesmo formato; `409` se o id não está pendente na sessão |
| `GET /sessoes/{id}/eventos` | `200` todos os eventos da sessão, em ordem |
| `GET /apartamentos/{n}/reservas` | `200 [{"codigo", "area", "data"}]` (reservas ativas) |
| `GET /apartamentos/{n}/visitantes` | `200 [{"nome", "data"}]` |

As rotas com `{id}` respondem `404` quando a sessão não existe. Uma falha ao chamar o modelo (por exemplo, limite de cota) responde `503`.
