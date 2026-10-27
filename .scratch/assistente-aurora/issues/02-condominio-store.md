# 02 Dados do condomínio, restauração e rotas de verificação

Status: ready-for-agent
Blocked by: 01

Ver `../spec.md` (Modelo de dados), ADR 0002.

## O que fazer

- `CondominioStore` em `condominio.py`:
  - Esquema com o índice único parcial e carga de `dados/*.json`.
  - Funções de domínio: listar reservas ativas do apartamento, disponibilidade, reservar com código único e `IntegrityError` tratado, cancelar como soft delete, listar e criar autorizações de visita.
  - Leitura de apartamentos e áreas.
- `aurora-restaurar`: apaga os dois bancos em `var/` e recria e semeia `condominio.db`.
- `aurora-api` sobe FastAPI em `:8000`. No startup, cria e semeia `condominio.db` só se ele não existir.
- Rotas `GET /apartamentos/{n}/reservas` (só ativas) e `GET /apartamentos/{n}/visitantes`.

## Aceite

- Passo 1 do avaliador: depois de restaurar e subir, o 101 lista `RSV-1377` e o 302 lista Marina Duarte.
- Dois `INSERT` concorrentes para a mesma área e data (script rápido com threads): exatamente um vence, e o outro recebe `indisponivel` sem exceção.
