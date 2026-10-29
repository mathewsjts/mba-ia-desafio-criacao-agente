# 11: Verificação em clone limpo

**What to build:** um avaliador que clona o fork consegue instalar, restaurar e subir a API seguindo só o README, e o repositório atende às checagens estáticas do passo 15. Nenhuma dessas verificações chama o modelo.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Num clone novo da branch, em diretório temporário, `uv sync` instala sem erro
- [x] No clone novo, os comandos de restauração e subida do README deixam a API respondendo em `http://localhost:8000`, e o passo 1 passa: 101 lista `RSV-1377` e 302 lista Marina Duarte
- [x] A versão exata do ADK está fixada (série 2, igual ou superior a 2.2.0) no `pyproject.toml` e no `uv.lock`
- [x] Os arquivos de `dados/` são idênticos aos do repositório base (commit inicial do enunciado)
- [x] Nenhuma chave nem `.env` está versionada em nenhum commit da branch, e o `.env.example` lista as variáveis sem valores
- [x] Todo arquivo e intervalo de linhas citado na seção Garantias do README existe e mostra o trecho descrito

## Comments

Verificado em 2026-10-28 sobre `feat/assistente-aurora` @ `813a903`, sem `GOOGLE_API_KEY` (nenhuma verificação chama o modelo).

- **uv sync:** `git clone --branch feat/assistente-aurora <repo> $SCRATCH/clone11`, depois `uv sync` (69 pacotes) e `uv sync --locked` sem erro, ou seja, o lock está em dia com o `pyproject.toml`. `google.adk.__version__` → `2.13.0`.
- **Restauração e subida:** no clone, `uv run aurora-restaurar` cria `var/condominio.db` e `uv run aurora-api` sobe em `:8000`.
  - `GET /apartamentos/101/reservas` → `200 [{"codigo":"RSV-1377","area":"quadra","data":"2030-03-09"}]`
  - `GET /apartamentos/302/visitantes` → `200 [{"nome":"Marina Duarte","data":"2030-03-16"}]`
  - `POST /sessoes {"apartamento":"101"}` → `201`.
  - Servidor parado em seguida, e a porta 8000 ficou livre.
- **ADK fixado:** `pyproject.toml` tem `google-adk[db]==2.13.0`, e o `uv.lock` tem `google-adk` `version = "2.13.0"` com specifier `==2.13.0`. É série 2 e ≥ 2.2.0.
- **dados/:** o commit inicial é `be87e1d` (`git log --reverse`). `git diff --quiet be87e1d feat/assistente-aurora -- dados/` → idêntico. `git log be87e1d..feat/assistente-aurora -- dados/` → 0 commits. No clone, `git status --porcelain` saiu vazio depois de restaurar e subir a API.
- **Segredos:** `git log --all --name-only --diff-filter=A` mostra só `.env.example` entre os arquivos `.env*` adicionados. No `git log -p --all`, a busca por `AIza…`, `sk-…`, `ghp_…`, `AKIA…` e por atribuições `*API_KEY|SECRET|TOKEN=<valor>` não achou nada. Todas as menções a `GOOGLE_API_KEY` são documentação ou `GOOGLE_API_KEY=` vazio. O `.env.example` lista `GOOGLE_API_KEY=` e `AURORA_MODEL=` sem valores, e `.env` está no `.gitignore`.
- **Garantias do README:** todos os links locais do README existem. Cada `arquivo:linha` e intervalo citado foi aberto e mostra o trecho descrito: `reservas.py` 37/64/127, `visitantes.py` 20/43/80, `confirmacoes.py` 22/43, `api.py` 38/111/118/120/128-144/130, `_comum.py` 11, `condominio.py` 34/85/113/124/138-158/161, `agentes/__init__.py` 13, `agentes/regulamento.py` 14/45. Nenhuma correção foi necessária.
- Nenhum código foi alterado. O repositório não versiona uma suíte de testes, e o clone limpo importou e serviu a API sem erro.
