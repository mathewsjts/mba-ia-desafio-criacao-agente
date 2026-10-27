"""API HTTP do assistente: rotas de conversa e rotas de verificação."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from aurora import condominio


@asynccontextmanager
async def lifespan(_: FastAPI):
    condominio.garantir_banco()
    yield


app = FastAPI(title="Assistente do Residencial Aurora", lifespan=lifespan)


@app.get("/apartamentos/{numero}/reservas")
def reservas_do_apartamento(numero: str) -> list[dict]:
    return condominio.listar_reservas(numero)


@app.get("/apartamentos/{numero}/visitantes")
def visitantes_do_apartamento(numero: str) -> list[dict]:
    return condominio.listar_autorizacoes(numero)
