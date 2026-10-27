"""Caminhos e configuração do assistente, lidos do ambiente e do .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]

load_dotenv(RAIZ / ".env")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

DADOS = RAIZ / "dados"
VAR = RAIZ / "var"
CONDOMINIO_DB = VAR / "condominio.db"
SESSOES_DB = VAR / "sessoes.db"

MODELO = os.environ.get("AURORA_MODEL") or "gemini-3.5-flash"

# O ADK exige app_name e user_id; o apartamento da sessão fica no state.
APP_NAME = "aurora"
USER_ID = "morador"
