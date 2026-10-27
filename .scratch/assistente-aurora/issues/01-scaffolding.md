# 01 Esqueleto do projeto

Status: ready-for-agent
Blocked by: —

Ver `../spec.md` (Stack e comandos, Layout de módulos).

## O que fazer

- Mover o enunciado de `README.md` para `docs/enunciado.md` e deixar um README provisório apontando para ele.
- Criar o projeto uv com Python 3.13: `.python-version`, `pyproject.toml` com `google-adk[db]==2.13.0` fixado, `fastapi`, `uvicorn`, layout `src/aurora/`, entrypoints `aurora-api` e `aurora-restaurar` e `uv.lock`.
- Criar `.env.example` com `GOOGLE_API_KEY`, `GOOGLE_GENAI_USE_VERTEXAI` e `AURORA_MODEL`, sem valores. Adicionar `var/` ao `.gitignore`.
- Criar `config.py` com os caminhos e o modelo.

## Aceite

- `uv sync` instala sem erro em clone limpo.
- `dados/` intacto (`git diff --stat dados/` vazio).
