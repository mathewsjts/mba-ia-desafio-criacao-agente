"""Comandos `aurora-api` e `aurora-restaurar`."""

import uvicorn

from aurora import condominio, config


def api() -> None:
    uvicorn.run("aurora.api:app", host="0.0.0.0", port=8000)


def restaurar() -> None:
    """Volta reservas e autorizações de visita ao estado de `dados/` e apaga todas as sessões."""
    for caminho in config.VAR.glob("*.db*"):
        caminho.unlink()
    condominio.criar_banco()
    print(f"Dados restaurados em {config.CONDOMINIO_DB}; sessões apagadas.")
