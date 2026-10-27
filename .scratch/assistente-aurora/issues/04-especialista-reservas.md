# 04 Especialista de reservas (sem confirmação)

Status: resolved
Blocked by: 03

Ver `../spec.md` (Agentes, Sessão e apartamento), ADR 0001.

## O que fazer

- `agentes/reservas.py`:
  - `LlmAgent` `mode="single_turn"`, com instrução dinâmica (lista de áreas e data de hoje).
  - Tools `listar_minhas_reservas`, `verificar_disponibilidade`, `reservar_area` e `cancelar_reserva`.
  - O apartamento vem só de `tool_context.state`.
  - As tools validam data e área.
- Ligar `reservas` como sub-agent do principal e ajustar a instrução de roteamento.
- Nesta issue, `reservar_area` ainda não pede confirmação: a confirmação é a issue 05. Para não violar a Garantia 1 entre as duas issues, área com taxa recusa a reserva com "ainda não suportado".

## Aceite

- Passo 3, parte de reservas: sem `RSV-4821` na resposta nem nos eventos.
- Passo 4: o 302 mantém a `RSV-4821`, que não aparece na resposta nem nos eventos.
- Passo 5: `RSV-1377` cancelada sem confirmação pendente.
- Passo 6: quadra em 2030-04-06 reservada sem confirmação.
