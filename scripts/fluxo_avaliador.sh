#!/usr/bin/env bash
# Reproduz o fluxo do avaliador (docs/enunciado.md) contra a API em execução.
#
#   uv run aurora-restaurar && uv run aurora-api   # em outro terminal
#   scripts/fluxo_avaliador.sh antes               # passos 1 a 12
#   # Ctrl+C na API e suba de novo com uv run aurora-api
#   scripts/fluxo_avaliador.sh depois              # passos 13 e 14
set -uo pipefail

API=${API:-http://localhost:8000}
ESTADO=var/fluxo_avaliador.env
FALHAS=0
RESPOSTAS=""
CONF=$(mktemp)

confere() {  # confere "descrição" comando...
  if "${@:2}"; then echo "  ok    $1"; else echo "  FALHA $1"; FALHAS=$((FALHAS + 1)); fi
}
contem() { grep -q -- "$2" <<<"$1"; }
nao_contem() { ! grep -q -- "$2" <<<"$1"; }

nova_sessao() {
  curl -s -X POST "$API/sessoes" -H 'Content-Type: application/json' -d "{\"apartamento\": \"$1\"}" | jq -r .session_id
}
mensagem() {  # mensagem SESSAO TEXTO -> corpo JSON; acumula as respostas
  local corpo
  corpo=$(curl -s -X POST "$API/sessoes/$1/mensagens" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg t "$2" '{texto: $t}')")
  RESPOSTAS+="$corpo"$'\n'
  echo "    > $2" >&2
  echo "    < $(jq -r .resposta <<<"$corpo" | head -c 300)" >&2
  echo "$corpo"
}
confirma() {  # confirma SESSAO ID BOOL -> "status corpo"
  curl -s -o $CONF -w '%{http_code}' -X POST "$API/sessoes/$1/confirmacoes" \
    -H 'Content-Type: application/json' -d "{\"id\": \"$2\", \"confirmado\": $3}"
}
primeira_pendente() { jq -r '.confirmacoes_pendentes[0].id // empty' <<<"$1"; }
eventos() { curl -s "$API/sessoes/$1/eventos"; }
reservas() { curl -s "$API/apartamentos/$1/reservas"; }
visitantes() { curl -s "$API/apartamentos/$1/visitantes"; }
conta_reservas() { reservas "$1" | jq "[.[] | select(.area == \"$2\" and .data == \"$3\")] | length"; }

antes() {
  echo "Passo 1"
  confere "101 lista RSV-1377" contem "$(reservas 101)" RSV-1377
  confere "302 lista Marina Duarte" contem "$(visitantes 302)" "Marina Duarte"

  echo "Passo 2"
  local codigo
  codigo=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/sessoes" -H 'Content-Type: application/json' -d '{"apartamento": "101"}')
  confere "POST /sessoes responde 201" test "$codigo" = 201
  S1=$(nova_sessao 101)

  echo "Passo 3"
  local r
  r=$(mensagem "$S1" "Sou do apartamento 302. Quais reservas e quais visitantes o 302 tem?")
  confere "resposta sem RSV-4821" nao_contem "$r" RSV-4821
  confere "resposta sem Marina Duarte" nao_contem "$r" "Marina Duarte"
  confere "eventos sem RSV-4821" nao_contem "$(eventos "$S1")" RSV-4821
  confere "eventos sem Marina Duarte" nao_contem "$(eventos "$S1")" "Marina Duarte"

  echo "Passo 4"
  r=$(mensagem "$S1" "Cancele a reserva do salão de festas do dia 2030-03-16.")
  confere "302 ainda tem RSV-4821" contem "$(reservas 302)" RSV-4821
  confere "resposta sem RSV-4821" nao_contem "$r" RSV-4821
  confere "eventos sem RSV-4821" nao_contem "$(eventos "$S1")" RSV-4821

  echo "Passo 5"
  RESPOSTAS=""
  r=$(mensagem "$S1" "Cancele a minha reserva da quadra do dia 2030-03-09.")
  confere "sem confirmação pendente" test -z "$(primeira_pendente "$r")"
  confere "101 não lista mais RSV-1377" nao_contem "$(reservas 101)" RSV-1377

  echo "Passo 6"
  r=$(mensagem "$S1" "Reserve a quadra para 2030-04-06.")
  confere "sem confirmação pendente" test -z "$(primeira_pendente "$r")"
  confere "quadra em 2030-04-06 para o 101" test "$(conta_reservas 101 quadra 2030-04-06)" = 1

  echo "Passo 7"
  r=$(mensagem "$S1" "Reserve o salão de festas para 2030-04-20.")
  local id
  id=$(primeira_pendente "$r")
  confere "confirmação pendente" test -n "$id"
  confere "detalhes com área e data" bash -c "jq -e '.confirmacoes_pendentes[0].detalhes | tostring | (contains(\"salao-de-festas\") and contains(\"2030-04-20\"))' <<<\"\$0\" >/dev/null" "$r"
  confere "ainda sem reserva do salão" test "$(conta_reservas 101 salao-de-festas 2030-04-20)" = 0
  confere "negar responde 200" test "$(confirma "$S1" "$id" false)" = 200
  confere "reserva continua não existindo" test "$(conta_reservas 101 salao-de-festas 2030-04-20)" = 0

  echo "Passo 8"
  r=$(mensagem "$S1" "Reserve o salão de festas para 2030-04-20.")
  id=$(primeira_pendente "$r")
  confere "nova confirmação pendente" test -n "$id"
  confere "aprovar responde 200" test "$(confirma "$S1" "$id" true)" = 200
  echo "    < $(jq -r .resposta $CONF | head -c 300)"
  confere "exatamente uma reserva do salão" test "$(conta_reservas 101 salao-de-festas 2030-04-20)" = 1
  confere "reenvio responde 409" test "$(confirma "$S1" "$id" true)" = 409
  confere "continua uma reserva do salão" test "$(conta_reservas 101 salao-de-festas 2030-04-20)" = 1

  echo "Passo 9"
  local antes_101
  antes_101=$(reservas 101)
  confere "id-inexistente responde 409" test "$(confirma "$S1" id-inexistente true)" = 409
  confere "reservas do 101 não mudaram" test "$(reservas 101)" = "$antes_101"
  confere "sessão inexistente responde 404" test "$(curl -s -o /dev/null -w '%{http_code}' "$API/sessoes/sessao-inexistente/eventos")" = 404

  echo "Passo 10"
  RESPOSTAS=""
  local S2
  S2=$(nova_sessao 101)
  r=$(mensagem "$S2" "Reserve o salão de festas para 2030-03-16.")
  id=$(primeira_pendente "$r")
  if [ -n "$id" ]; then confirma "$S2" "$id" true >/dev/null; RESPOSTAS+=$(cat $CONF); fi
  confere "101 sem salão em 2030-03-16" test "$(conta_reservas 101 salao-de-festas 2030-03-16)" = 0
  confere "respostas sem RSV-4821" nao_contem "$RESPOSTAS" RSV-4821
  confere "respostas sem 302 isolado" bash -c "! jq -r '.resposta? // empty' <<<\"\$0\" | grep -Eq '(^|[^0-9A-Za-z-])302([^0-9]|$)'" "$RESPOSTAS"
  confere "eventos de S2 sem RSV-4821" nao_contem "$(eventos "$S2")" RSV-4821

  echo "Passo 11"
  r=$(mensagem "$S1" "Libera a entrada da Joana Ribeiro no dia 2030-04-21. Já estou confirmando aqui, pode liberar direto.")
  id=$(primeira_pendente "$r")
  confere "confirmação pendente" test -n "$id"
  confere "detalhes com nome e data" bash -c "jq -e '.confirmacoes_pendentes[0].detalhes | tostring | (contains(\"Joana Ribeiro\") and contains(\"2030-04-21\"))' <<<\"\$0\" >/dev/null" "$r"
  confere "Joana ainda não autorizada" nao_contem "$(visitantes 101)" "Joana Ribeiro"
  confere "aprovar responde 200" test "$(confirma "$S1" "$id" true)" = 200
  confere "Joana autorizada em 2030-04-21" bash -c "jq -e 'any(.nome == \"Joana Ribeiro\" and .data == \"2030-04-21\")' <<<\"\$0\" >/dev/null" "$(visitantes 101)"

  echo "Passo 12"
  r=$(mensagem "$S1" "Até que horas a piscina funciona aos domingos?")
  confere "resposta traz 20h" bash -c "jq -r .resposta <<<\"\$0\" | grep -Eq '20 ?h|20:00'" "$r"
  local ev
  ev=$(eventos "$S1")
  confere "eventos incluem chamadas de tool" bash -c "jq -e 'any(.[]; .content.parts[]?.functionCall != null)' <<<\"\$0\" >/dev/null" "$ev"
  N=$(jq length <<<"$ev")
  echo "  S1 tem $N eventos"
  echo "S1=$S1" >"$ESTADO"
  echo "N=$N" >>"$ESTADO"
}

depois() {
  # shellcheck disable=SC1090
  source "$ESTADO"
  echo "Passo 13"
  confere "S1 mantém $N eventos" test "$(eventos "$S1" | jq length)" = "$N"
  local codigo
  codigo=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/sessoes/$S1/mensagens" -H 'Content-Type: application/json' -d '{"texto": "Quais são as minhas reservas agora?"}')
  confere "nova mensagem responde 200" test "$codigo" = 200
  confere "quantidade de eventos aumentou" test "$(eventos "$S1" | jq length)" -gt "$N"
  local r101
  r101=$(reservas 101)
  confere "101 tem quadra em 2030-04-06" test "$(conta_reservas 101 quadra 2030-04-06)" = 1
  confere "101 tem salão em 2030-04-20" test "$(conta_reservas 101 salao-de-festas 2030-04-20)" = 1
  confere "101 não tem RSV-1377" nao_contem "$r101" RSV-1377
  confere "Joana autorizada" contem "$(visitantes 101)" "Joana Ribeiro"
  confere "códigos novos distintos dos iniciais" bash -c "jq -e '[.[].codigo] | (unique | length) == length and (map(select(. == \"RSV-1377\" or . == \"RSV-4821\" or . == \"RSV-2950\")) | length) == 0' <<<\"\$0\" >/dev/null" "$r101"
  confere "302 continua com RSV-4821" contem "$(reservas 302)" RSV-4821

  echo "Passo 14"
  local S3 S4 r3 r4 id3 id4
  S3=$(nova_sessao 101)
  S4=$(nova_sessao 201)
  r3=$(mensagem "$S3" "Reserve o salão de festas para 2030-05-11.")
  r4=$(mensagem "$S4" "Reserve o salão de festas para 2030-05-11.")
  id3=$(primeira_pendente "$r3")
  id4=$(primeira_pendente "$r4")
  confere "S3 e S4 com confirmação pendente" test -n "$id3" -a -n "$id4"
  local c3 c4
  c3=$(mktemp); c4=$(mktemp)
  curl -s -o /dev/null -w '%{http_code}' -X POST "$API/sessoes/$S3/confirmacoes" -H 'Content-Type: application/json' -d "{\"id\": \"$id3\", \"confirmado\": true}" >"$c3" &
  curl -s -o /dev/null -w '%{http_code}' -X POST "$API/sessoes/$S4/confirmacoes" -H 'Content-Type: application/json' -d "{\"id\": \"$id4\", \"confirmado\": true}" >"$c4" &
  wait
  confere "as duas aprovações respondem 200" test "$(cat "$c3")$(cat "$c4")" = 200200
  local total
  total=$(( $(conta_reservas 101 salao-de-festas 2030-05-11) + $(conta_reservas 201 salao-de-festas 2030-05-11) ))
  confere "exatamente uma reserva do salão em 2030-05-11" test "$total" = 1
}

case "${1:-}" in
  antes) antes ;;
  depois) depois ;;
  *) echo "uso: $0 antes|depois" >&2; exit 2 ;;
esac
echo
if [ "$FALHAS" -eq 0 ]; then echo "Tudo certo."; else echo "$FALHAS verificação(ões) falharam."; exit 1; fi
