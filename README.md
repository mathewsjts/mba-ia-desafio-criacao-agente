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
| `visitantes` ([agentes/visitantes.py](src/aurora/agentes/visitantes.py)) | Lista e cria autorizações de visita. | Sub-agent `mode="single_turn"`, como o de reservas. | Mesmo motivo: `autorizar_visitante` sempre pede confirmação. |
| `regulamento` ([agentes/regulamento.py](src/aurora/agentes/regulamento.py)) | Responde dúvidas lendo um capítulo do regulamento por vez. | `AgentTool` no agente principal. | O `AgentTool` roda o especialista numa sessão descartável: o capítulo lido nunca entra nos eventos da sessão do morador, só a resposta final. |

Escolhas de suporte:

- **ADK `google-adk[db]==2.13.0`**. A partir dessa versão, o Runner encaminha a resposta de uma confirmação ao agente que a pediu, qualquer que seja a topologia. Nas versões anteriores, a resposta podia cair em outro agente e ser ignorada em silêncio.
- **Modelo:** um único modelo Gemini para todos os agentes, configurável em `AURORA_MODEL` (padrão `gemini-3.5-flash`).
- **Armazenamento:** SQLite, sem serviço externo ([ADR 0002](docs/adr/0002-sqlite-com-indice-unico-parcial.md)). As sessões ficam no `DatabaseSessionService` do ADK, em `var/sessoes.db`, e os dados do condomínio em `var/condominio.db`. Os arquivos de `dados/` só são lidos, nunca alterados.

## Garantias

### 1. Cobrança ou acesso só com confirmação

- **Quem decide se pede confirmação é o código.**
  - [agentes/reservas.py:37](src/aurora/agentes/reservas.py#L37) `_gera_cobranca`: verdadeiro para área com `taxa > 0`, ligado em `FunctionTool(reservar_area, require_confirmation=_gera_cobranca)` ([linha 127](src/aurora/agentes/reservas.py#L127)).
  - [agentes/visitantes.py:20](src/aurora/agentes/visitantes.py#L20) `_libera_acesso`: toda autorização nova ([linha 80](src/aurora/agentes/visitantes.py#L80)).
  - O ADK só executa o corpo dessas tools depois de uma resposta `adk_request_confirmation`, e área sem taxa não pede confirmação.
- **Defesa extra no corpo das tools.** Sem uma aprovação, `reservar_area` não grava reserva com cobrança ([reservas.py:64](src/aurora/agentes/reservas.py#L64)) e `autorizar_visitante` não grava autorização ([visitantes.py:43](src/aurora/agentes/visitantes.py#L43)).
- **A confirmação vem do sistema, não da conversa.**
  - [confirmacoes.py:22](src/aurora/confirmacoes.py#L22) `pendentes` lê dos eventos da sessão as chamadas `adk_request_confirmation` ainda sem resposta.
  - A rota [api.py:128-144](src/aurora/api.py#L128-L144) só aceita um `id` dessa lista. Qualquer outro id, inclusive um já respondido, recebe `409` antes de chegar ao Runner, então aprovar executa uma única vez.
  - Enquanto há pendência, uma nova mensagem nem chama o modelo ([api.py:120](src/aurora/api.py#L120)), então "já estou confirmando aqui" não aprova nada.
- **Verificação depois de aprovar.** [confirmacoes.py:43](src/aurora/confirmacoes.py#L43) `acao_executada` confere que a tool aprovada rodou de fato e registra um aviso se não rodou.

### 2. Cada sessão pertence a um apartamento

- **O apartamento é gravado uma única vez**, no state da sessão, na criação ([api.py:111](src/aurora/api.py#L111)). Apartamento inexistente recebe `422`.
- **Nenhuma tool recebe apartamento como parâmetro.** Todas o leem do state por [agentes/\_comum.py:11](src/aurora/agentes/_comum.py#L11) `apartamento_da_sessao`, e o modelo não tem como escrever no state.
- **As consultas e gravações filtram pelo apartamento** ([condominio.py:113](src/aurora/condominio.py#L113) `listar_reservas`, [condominio.py:161](src/aurora/condominio.py#L161) `cancelar`, autorizações idem). Cancelar a reserva de outro apartamento devolve "não encontrada".
- **A disponibilidade não revela o dono.** Ela é consultada por [condominio.py:124](src/aurora/condominio.py#L124) `area_livre`, que devolve só livre ou ocupada. Reservar uma data ocupada devolve só `indisponivel`, então nenhum código, nome ou número de outro apartamento chega à conversa.

### 3. Nada se perde no reinício

- **Sessões e eventos** ficam no `DatabaseSessionService` em SQLite ([api.py:38](src/aurora/api.py#L38)).
- **Reservas e autorizações** ficam em `var/condominio.db`.
- **Subir a API não reseta nada.** O startup só cria o banco se ele não existir ([condominio.py:85](src/aurora/condominio.py#L85) `garantir_banco`); só `aurora-restaurar` volta ao estado inicial.
- **Confirmações sobrevivem ao reinício.** Uma confirmação pendente antes do reinício pode ser aprovada depois, porque as pendências são lidas dos eventos persistidos.
- **Nenhum código de reserva se repete.** Cancelar muda o status para `cancelada` em vez de apagar, então a chave primária em `codigo` cobre também os códigos de reservas canceladas.

### 4. O regulamento é consultado, não carregado

- **O agente principal não recebe o regulamento.** A instrução dele ([agentes/\_\_init\_\_.py:13](src/aurora/agentes/__init__.py#L13)) só diz para encaminhar dúvidas ao especialista.
- **O especialista lê um capítulo por vez.** A instrução dele traz apenas o índice de capítulos, e [agentes/regulamento.py:14](src/aurora/agentes/regulamento.py#L14) `ler_capitulo` devolve um único capítulo. Cada capítulo trata de um único assunto ([regulamento.py](src/aurora/regulamento.py)).
- **O texto do capítulo não entra na sessão.** O especialista é um `AgentTool` ([agentes/regulamento.py:45](src/aurora/agentes/regulamento.py#L45)), que roda numa sessão em memória descartável. Só a resposta final volta aos eventos da sessão do morador.

### 5. Dois moradores, uma reserva

- **A exclusividade vale no instante da gravação.** Ela é garantida pelo índice único parcial [condominio.py:34](src/aurora/condominio.py#L34): `CREATE UNIQUE INDEX reserva_ativa_unica ON reservas(area, data) WHERE status = 'ativa'`.
- **A segunda gravação é recusada sem erro de servidor.** Quando duas aprovações chegam ao mesmo tempo, as duas podem ter visto a data livre, mas o SQLite serializa as escritas e o segundo `INSERT` falha com `IntegrityError`. [condominio.py:138-159](src/aurora/condominio.py#L138-L159) `reservar` o traduz em `None`, e a tool responde `indisponivel` normalmente, com `200`.
- **Requisições na mesma sessão não colidem.** Um `asyncio.Lock` por sessão ([api.py:118](src/aurora/api.py#L118), [api.py:130](src/aurora/api.py#L130)) evita que duas requisições simultâneas na mesma sessão gravem eventos concorrentes.

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
| `AURORA_MODEL` | não | Modelo Gemini usado por todos os agentes. Padrão: `gemini-3.5-flash`. |

### Comandos

```bash
uv sync                 # instala as dependências (google-adk[db]==2.13.0 fixado)
uv run aurora-restaurar # volta reservas e visitantes ao estado de dados/ e apaga as sessões
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
