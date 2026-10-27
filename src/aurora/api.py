"""API HTTP do assistente: rotas de conversa e rotas de verificação."""

import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import Session
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from aurora import condominio, config, confirmacoes
from aurora.agentes import criar_app

logger = logging.getLogger("aurora")

AVISO_PENDENCIA = (
    "Você tem uma confirmação pendente. Aprove ou negue pelo aplicativo antes de fazer um novo pedido."
)

session_service: DatabaseSessionService
runner: Runner
# Duas execuções simultâneas na mesma sessão gravariam eventos concorrentes
# (StaleSessionError); o lock serializa mensagens e confirmações por sessão.
locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global session_service, runner
    condominio.garantir_banco()
    config.VAR.mkdir(parents=True, exist_ok=True)
    session_service = DatabaseSessionService(f"sqlite+aiosqlite:///{config.SESSOES_DB}")
    runner = Runner(app=criar_app(), session_service=session_service)
    yield
    await runner.close()


app = FastAPI(title="Assistente do Residencial Aurora", lifespan=lifespan)


class NovaSessao(BaseModel):
    apartamento: str


class Mensagem(BaseModel):
    texto: str


class RespostaConfirmacao(BaseModel):
    id: str
    confirmado: bool


async def _buscar_sessao(session_id: str) -> Session:
    sessao = await session_service.get_session(
        app_name=config.APP_NAME, user_id=config.USER_ID, session_id=session_id
    )
    if sessao is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return sessao


def _texto_da_resposta(eventos: list[Event]) -> str:
    """Texto final que o agente principal escreveu nesta execução."""
    raiz = runner.agent.name
    textos = [
        "".join(parte.text or "" for parte in evento.content.parts if not parte.thought)
        for evento in eventos
        if evento.author == raiz
        and not evento.partial
        and evento.content
        and evento.content.parts
    ]
    return "\n".join(texto for texto in textos if texto.strip())


async def _executar(session_id: str, conteudo: types.Content) -> list[Event]:
    eventos = []
    try:
        async for evento in runner.run_async(
            user_id=config.USER_ID, session_id=session_id, new_message=conteudo
        ):
            eventos.append(evento)
    except genai_errors.APIError as erro:
        logger.exception("Falha ao chamar o modelo")
        raise HTTPException(
            status_code=503, detail=f"O modelo não respondeu: {erro.message}"
        ) from erro
    return eventos


async def _resposta(session_id: str, texto: str) -> dict:
    sessao = await _buscar_sessao(session_id)
    return {"resposta": texto, "confirmacoes_pendentes": confirmacoes.pendentes(sessao.events)}


@app.post("/sessoes", status_code=201)
async def criar_sessao(corpo: NovaSessao) -> dict:
    if not condominio.apartamento_existe(corpo.apartamento):
        raise HTTPException(status_code=422, detail="Apartamento inexistente.")
    # Garantia 2: o apartamento é fixado aqui, uma única vez, e as tools só o leem do state.
    sessao = await session_service.create_session(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        state={"apartamento": corpo.apartamento},
    )
    return {"session_id": sessao.id}


@app.post("/sessoes/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, corpo: Mensagem) -> dict:
    async with locks[session_id]:
        sessao = await _buscar_sessao(session_id)
        if pendentes := confirmacoes.pendentes(sessao.events):
            # Nada executa sem confirmação: enquanto houver pendência, o modelo nem é chamado.
            return {"resposta": AVISO_PENDENCIA, "confirmacoes_pendentes": pendentes}
        conteudo = types.Content(role="user", parts=[types.Part(text=corpo.texto)])
        eventos = await _executar(session_id, conteudo)
        return await _resposta(session_id, _texto_da_resposta(eventos))


@app.post("/sessoes/{session_id}/confirmacoes")
async def responder_confirmacao(session_id: str, corpo: RespostaConfirmacao) -> dict:
    async with locks[session_id]:
        sessao = await _buscar_sessao(session_id)
        # Garantia 1: só um id pendente nesta sessão retoma a execução; um id desconhecido
        # ou já respondido recebe 409 sem chegar ao Runner.
        if corpo.id not in {p["id"] for p in confirmacoes.pendentes(sessao.events)}:
            raise HTTPException(
                status_code=409, detail="Não há confirmação pendente com esse id nesta sessão."
            )
        eventos = await _executar(session_id, confirmacoes.resposta(corpo.id, corpo.confirmado))
        resposta = await _resposta(session_id, _texto_da_resposta(eventos))
        if corpo.confirmado:
            sessao = await _buscar_sessao(session_id)
            if not confirmacoes.acao_executada(sessao.events, corpo.id):
                logger.warning("Confirmação %s aprovada, mas a ação não executou.", corpo.id)
        return resposta


@app.get("/sessoes/{session_id}/eventos")
async def listar_eventos(session_id: str) -> list[dict]:
    sessao = await _buscar_sessao(session_id)
    return [
        evento.model_dump(mode="json", exclude_none=True, by_alias=True)
        for evento in sessao.events
    ]


@app.get("/apartamentos/{numero}/reservas")
def reservas_do_apartamento(numero: str) -> list[dict]:
    return condominio.listar_reservas(numero)


@app.get("/apartamentos/{numero}/visitantes")
def visitantes_do_apartamento(numero: str) -> list[dict]:
    return condominio.listar_autorizacoes(numero)
