"""Confirmações pendentes, lidas dos eventos da sessão (Garantia 1).

Uma confirmação está pendente quando há uma chamada `adk_request_confirmation`
sem resposta com o mesmo id. A rota de confirmações só aceita esses ids, o que
impede que uma confirmação já respondida execute a ação de novo.
"""

from google.adk.events import Event
from google.genai import types

FUNCAO_CONFIRMACAO_ADK = "adk_request_confirmation"


def _chamada_original(args: dict) -> dict:
    return args.get("originalFunctionCall") or args.get("original_function_call") or {}


def _ids_respondidos(eventos: list[Event]) -> set[str]:
    return {resposta.id for evento in eventos for resposta in evento.get_function_responses()}


def _pedidos_de_confirmacao(eventos: list[Event]) -> list[types.FunctionCall]:
    return [
        chamada
        for evento in eventos
        for chamada in evento.get_function_calls()
        if chamada.name == FUNCAO_CONFIRMACAO_ADK
    ]


def pendentes(eventos: list[Event]) -> list[dict]:
    respondidos = _ids_respondidos(eventos)
    lista = []
    for chamada in _pedidos_de_confirmacao(eventos):
        if chamada.id in respondidos:
            continue
        original = _chamada_original(chamada.args)
        lista.append(
            {"id": chamada.id, "acao": original.get("name"), "detalhes": original.get("args", {})}
        )
    return lista


def decisao_do_morador(confirmacao_id: str, confirmado: bool) -> types.Content:
    """Mensagem que devolve a decisão do morador ao Runner, que retoma a tool pendente."""
    return types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
        name=FUNCAO_CONFIRMACAO_ADK, id=confirmacao_id, response={"confirmed": confirmado},
    ))])


def acao_executada(eventos: list[Event], confirmacao_id: str) -> bool:
    """Confere que a tool aprovada rodou de fato, e não só ficou com a resposta provisória."""
    chamada_original_id = next(
        (
            _chamada_original(chamada.args).get("id")
            for chamada in _pedidos_de_confirmacao(eventos)
            if chamada.id == confirmacao_id
        ),
        None,
    )
    return any(
        resposta.id == chamada_original_id
        and "requires confirmation" not in str(resposta.response)
        for evento in eventos
        for resposta in evento.get_function_responses()
    )
