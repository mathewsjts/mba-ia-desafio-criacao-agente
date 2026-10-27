# 07 Especialista do regulamento

Status: ready-for-agent
Blocked by: 03

Ver `../spec.md` (Agentes), ADR 0001.

## O que fazer

- `regulamento.py`: dividir `dados/regulamento.md` em capítulos (número romano, título e texto).
- `agentes/regulamento.py`:
  - `LlmAgent` cuja instrução traz só o índice de capítulos.
  - Tool `ler_capitulo(numero)` devolve um único capítulo.
- Expor o especialista como `AgentTool` no agente principal. O principal não recebe o regulamento nas instruções.

## Aceite

- Passo 12: a resposta traz o fechamento da piscina aos domingos (20h).
- Nenhum evento da sessão contém texto de capítulos que não sejam o IV.
