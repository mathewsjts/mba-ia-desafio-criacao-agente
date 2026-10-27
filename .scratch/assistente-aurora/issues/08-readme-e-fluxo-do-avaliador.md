# 08 README final e script do fluxo do avaliador

Status: resolved
Blocked by: 05, 06, 07

Ver `../spec.md` (Critério de pronto) e `docs/enunciado.md` (Fluxo do avaliador, Entregável).

## O que fazer

- `scripts/fluxo_avaliador.sh` (ferramenta de desenvolvimento) executa os passos 1–14 com curl e jq e imprime as verificações.
- README final com:
  - **Arquitetura:** cada agente, responsabilidade, como é acionado e por quê.
  - **Garantias:** para cada uma das cinco, arquivo e trecho reais e por que não depende do modelo.
  - **Como rodar:** pré-requisitos, `.env`, comandos de subida e restauração.
  - Link para `docs/enunciado.md`.

## Aceite

- [x] O script passa nos passos 1–14 com o modelo falso roteirizado, incluindo o reinício real do processo entre "antes" e "depois".
- [x] Todas as referências do README apontam para arquivos e trechos que existem.

A execução com o modelo real foi movida para a issue 10, e a verificação em clone limpo (passo 15) para a issue 11.
