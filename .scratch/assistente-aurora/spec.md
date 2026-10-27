# Spec: assistente virtual do Residencial Aurora

Status: ready-for-agent

Enunciado completo: `docs/enunciado.md` (hoje ainda em `README.md`, movido na issue 01). Vocabulário: `GLOSSARY.md`. Decisões de fundo: `docs/adr/0001-*` e `docs/adr/0002-*`.

## Problema

Os moradores precisam reservar áreas comuns, cancelar as próprias reservas, autorizar visitas e tirar dúvidas sobre o regulamento por um chat. O modelo conduz a conversa, mas as regras críticas precisam valer no código, não importa o que o morador escreva: cobrança e acesso só com confirmação do sistema, isolamento por apartamento, persistência no reinício, regulamento consultado sob demanda e exclusividade da reserva sob concorrência.

## Solução

Uma API FastAPI em `http://localhost:8000` que expõe um assistente Google ADK 2.13.0. O agente principal distribui o trabalho entre três especialistas. Sessões e dados do condomínio persistem em SQLite.

## Stack e comandos

- Python 3.13 gerenciado por uv (`.python-version`, `pyproject.toml`, `uv.lock` versionados).
- `google-adk[db]==2.13.0` fixado (o extra `db` traz SQLAlchemy para `DatabaseSessionService`), `fastapi`, `uvicorn`.
- `.env` (fora do Git), com o `.env.example` versionado:
  - `GOOGLE_API_KEY`: chave do Google AI Studio.
  - `GOOGLE_GENAI_USE_VERTEXAI=FALSE`.
  - `AURORA_MODEL`: opcional, padrão `gemini-3.5-flash`. Um único modelo para todos os agentes.
- `uv run aurora-api` sobe a API em `0.0.0.0:8000`.
- `uv run aurora-restaurar` apaga `var/condominio.db` e `var/sessoes.db`, recria o esquema e carrega `dados/*.json`.
- Ao subir, a API cria e semeia `var/condominio.db` **só se ele não existir**. Nunca reseta um banco existente.
- `var/` fica no `.gitignore`. Os arquivos em `dados/` nunca são alterados.

## Layout de módulos

```
src/aurora/
  config.py          caminhos (dados/, var/), modelo, nomes de app/usuário do ADK
  condominio.py      CondominioStore: esquema, carga inicial, consultas e gravações de domínio (SQLite)
  regulamento.py     leitura do regulamento.md e divisão em capítulos
  agentes/
    __init__.py      monta o agente principal e o App
    reservas.py      especialista + tools de reserva
    visitantes.py    especialista + tools de autorização de visita
    regulamento.py   especialista do regulamento (AgentTool) + ler_capitulo
  confirmacoes.py    extrai confirmações pendentes dos eventos e monta a resposta para o Runner
  api.py             FastAPI: rotas, Runner, lock por sessão
  cli.py             entrypoints aurora-api e aurora-restaurar
```

## Modelo de dados (`var/condominio.db`)

- `apartamentos(numero PK, morador)`
- `areas(id PK, nome, taxa REAL)`
- `reservas(codigo PK, apartamento, area, data TEXT, status TEXT CHECK IN ('ativa','cancelada'))`
  - `CREATE UNIQUE INDEX reserva_ativa_unica ON reservas(area, data) WHERE status = 'ativa'`
  - Os dados iniciais entram com `status='ativa'`.
- `autorizacoes_visita(id PK autoincrement, apartamento, nome, data, UNIQUE(apartamento, nome, data))`

Regras:

- **Cancelar** faz `UPDATE ... SET status='cancelada' WHERE apartamento=? AND area=? AND data=? AND status='ativa'`. Nunca apaga a linha.
- **Código novo:** `RSV-` + 6 caracteres de `[A-Z0-9]` aleatórios. Se a PK colidir, gera outro e tenta de novo. A colisão é distinguida da colisão do índice `(area, data)` pelo nome da constraint ou por checagem do código.
- **Reservar** é um `INSERT` em transação curta. `IntegrityError` no índice parcial vira `{"status": "indisponivel"}`, nunca exceção para a API.
- Conexões `sqlite3` com `timeout` alto (ex.: 30 s), uma conexão por operação.

## Sessão e apartamento (Garantia 2)

- `POST /sessoes {"apartamento"}`:
  - Valida contra `apartamentos`. Inexistente responde `422`.
  - Cria a sessão no `DatabaseSessionService("sqlite+aiosqlite:///var/sessoes.db")` com `app_name="aurora"`, `user_id="morador"` constante e `state={"apartamento": numero}`.
  - Responde `201 {"session_id"}`.
- As tools leem o apartamento **só** de `tool_context.state["apartamento"]`. Nenhuma tool tem parâmetro de apartamento.
- Nenhuma tool devolve código, apartamento, morador ou visitante de outro apartamento:
  - `verificar_disponibilidade` devolve só `livre`/`ocupada`.
  - Reservar data ocupada devolve só `indisponivel`.
  - Cancelar algo que não é do apartamento devolve "você não tem reserva dessa área nessa data".
- Não há filtro na saída do modelo: a proteção está nas tools.

## Agentes (ADR 0001)

- **`assistente_aurora`** (raiz, `LlmAgent` modo chat):
  - Instrução de roteamento, sem regulamento, sem tools de domínio.
  - `sub_agents=[reservas, visitantes]` e `tools=[AgentTool(regulamento)]`.
- **`reservas`** (`mode="single_turn"`): instrução com a lista de áreas (id, nome, taxa) e a data de hoje, via instruction provider. Tools:
  - `listar_minhas_reservas()`: só as reservas ativas do apartamento.
  - `verificar_disponibilidade(area, data)`: `livre`/`ocupada`.
  - `reservar_area(area, data)`:
    - `FunctionTool(..., require_confirmation=lambda area, data: taxa(area) > 0)`.
    - Antes de pedir confirmação, o especialista é instruído a verificar a disponibilidade.
    - O corpo valida de novo, e o índice garante a exclusividade no `INSERT`.
    - Devolve `{"status": "reservada", "codigo", "area", "data", "cobranca": bool, "taxa"}` ou `indisponivel`.
  - `cancelar_reserva(area, data)`: sem confirmação, restrita ao apartamento da sessão.
- **`visitantes`** (`mode="single_turn"`): instrução com a data de hoje. Tools:
  - `listar_minhas_autorizacoes()`.
  - `autorizar_visitante(nome, data)`:
    - `require_confirmation=True` sempre.
    - Uma duplicata exata (mesmo apartamento, nome e data) é tratada como já autorizada. O especialista consulta `listar_minhas_autorizacoes` antes. Se a duplicata chegar ao corpo, o `UNIQUE` devolve `ja_autorizada` sem segundo registro.
- **`regulamento`** (exposto via `AgentTool`, roda numa sessão descartável):
  - A instrução traz só o índice de capítulos (número romano + título).
  - Tool `ler_capitulo(numero)` devolve o texto de um único capítulo.
  - Só a resposta final do especialista entra nos eventos da sessão (Garantia 4).
- Validação nas tools: `data` precisa casar `AAAA-MM-DD` e ser data válida, e `area` precisa ser um id de `areas`. Fora disso, a tool devolve erro normal (`{"status": "invalido", "motivo": ...}`).

## Confirmações (Garantia 1)

- **Pendentes** = chamadas `adk_request_confirmation` nos eventos da sessão cujo `id` não tem `function_response` com o mesmo id. Para cada uma:
  - `id` = id da chamada `adk_request_confirmation`.
  - `acao` = `originalFunctionCall.name`.
  - `detalhes` = `originalFunctionCall.args` (área e data, ou nome e data).
- **`POST /sessoes/{id}/confirmacoes {"id", "confirmado"}`**, dentro do lock da sessão:
  - Se o `id` não está entre as pendentes da sessão, responde `409`, sem chamar o Runner.
  - Senão, chama `runner.run_async` com `Content(role="user", parts=[FunctionResponse(name="adk_request_confirmation", id=id, response={"confirmed": confirmado})])`.
  - Depois de aprovar, confere nos eventos que existe uma resposta real (não o placeholder "requires confirmation") para o id da chamada original. Se não houver, registra um warning no log.
- **`POST /sessoes/{id}/mensagens`** com confirmação pendente: responde `200` sem chamar o modelo, com `resposta` pedindo que o morador responda a confirmação primeiro e a lista atual em `confirmacoes_pendentes`.
- Negar: a tool devolve "rejected", nada é gravado, e o modelo responde.

## API

Todas as rotas usam JSON. As rotas com `{session_id}` respondem `404` se a sessão não existe.

| Rota | Comportamento |
|---|---|
| `POST /sessoes` | `201 {"session_id"}`; `422` para apartamento inexistente |
| `POST /sessoes/{id}/mensagens` `{"texto"}` | `200 {"resposta", "confirmacoes_pendentes"}` |
| `POST /sessoes/{id}/confirmacoes` `{"id","confirmado"}` | `200` mesmo formato; `409` se o id não está pendente na sessão |
| `GET /sessoes/{id}/eventos` | `200` lista de todos os eventos, em ordem, `event.model_dump(mode="json", exclude_none=True, by_alias=True)` |
| `GET /apartamentos/{n}/reservas` | `200 [{"codigo","area","data"}]`, só ativas; `[]` para apartamento inexistente |
| `GET /apartamentos/{n}/visitantes` | `200 [{"nome","data"}]`; `[]` para apartamento inexistente |

Detalhes:

- **`resposta`:** concatena o texto (sem `thought`) dos eventos finais da invocação atual escritos por agentes. Pode ser `""` quando a execução parou esperando confirmação.
- **`confirmacoes_pendentes`:** calculada a partir da sessão relida depois da execução.
- **Lock por sessão:** um `asyncio.Lock` por `session_id` serializa mensagens e confirmações da mesma sessão. Isso evita `StaleSessionError`, e a checagem de 409 acontece dentro do lock.
- **Erros do modelo** (ex.: rate limit) viram um erro HTTP claro (`503`) em vez de stack trace. Eles não fazem parte do contrato.

## Fora de escopo

- Interface visual, autenticação real, pagamento e estorno.
- Antecedência, datas passadas, horários e capacidade.
- Cancelamento de autorização de visita.
- Testes automatizados e evals. Um script de fumaça que reproduz o fluxo do avaliador é permitido como ferramenta de desenvolvimento.

## Critério de pronto

Os passos 1–15 do fluxo do avaliador em `docs/enunciado.md` passam com a chave real, incluindo o reinício do passo 13 e a disputa concorrente do passo 14. O README tem as seções Arquitetura, Garantias (com arquivo e trecho reais) e Como rodar.
