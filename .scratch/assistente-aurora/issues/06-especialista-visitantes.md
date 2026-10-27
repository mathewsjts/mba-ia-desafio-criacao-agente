# 06 Especialista de autorizações de visita

Status: resolved
Blocked by: 05

Ver `../spec.md` (Agentes).

## O que fazer

- `agentes/visitantes.py`:
  - `LlmAgent` `mode="single_turn"`, com instrução dinâmica (data de hoje).
  - `listar_minhas_autorizacoes` e `autorizar_visitante(nome, data)` com `require_confirmation=True`.
  - Duplicata exata tratada como já autorizada.
- Ligar `visitantes` como sub-agent do principal.

## Aceite

- Passo 3, parte de visitantes: sem Marina Duarte na resposta nem nos eventos.
- Passo 11: pendência com nome e data em `detalhes`, mesmo com "já estou confirmando aqui"; nada gravado antes da aprovação; depois de aprovar, Joana Ribeiro aparece em 2030-04-21.
