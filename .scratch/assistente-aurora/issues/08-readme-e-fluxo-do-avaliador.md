# 08 README final e fluxo do avaliador ponta a ponta

Status: ready-for-agent
Blocked by: 05, 06, 07

Ver `../spec.md` (Critério de pronto) e `docs/enunciado.md` (Fluxo do avaliador, Entregável).

## O que fazer

- `scripts/fluxo_avaliador.sh` (ferramenta de desenvolvimento) executa os passos 1–14 com curl e jq e imprime as verificações.
- Rodar o fluxo com a chave real, incluindo o reinício do passo 13 e a disputa do passo 14, e corrigir o que falhar.
- README final com:
  - **Arquitetura:** cada agente, responsabilidade, como é acionado e por quê.
  - **Garantias:** para cada uma das cinco, arquivo e trecho reais e por que não depende do modelo.
  - **Como rodar:** pré-requisitos, `.env`, comandos de subida e restauração.
  - Link para `docs/enunciado.md`.

## Aceite

- Fluxo 1–15 passando.
- Todas as referências do README apontam para arquivos e trechos que existem.
