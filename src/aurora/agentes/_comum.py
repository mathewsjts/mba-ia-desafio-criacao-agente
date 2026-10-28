"""Validações e trechos de instrução compartilhados pelos especialistas."""

from datetime import date

from google.adk.tools import ToolContext

DIAS_DA_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                  "sexta-feira", "sábado", "domingo"]


def apartamento_da_sessao(tool_context: ToolContext) -> str:
    """Garantia 2: o apartamento vem do state gravado na criação da sessão, nunca do modelo."""
    return tool_context.state["apartamento"]


def aprovada_pelo_morador(tool_context: ToolContext) -> bool:
    """Garantia 1: só o ADK preenche `tool_confirmation`, a partir da resposta da rota de
    confirmações; o modelo não tem como escrever nele."""
    confirmacao = tool_context.tool_confirmation
    return bool(confirmacao and confirmacao.confirmed)


def data_invalida(data: str) -> dict | None:
    """Devolve o erro para a tool repassar, ou None se a data está em AAAA-MM-DD válido."""
    try:
        if date.fromisoformat(data).isoformat() == data:
            return None
    except ValueError:
        pass
    return {"status": "invalido", "motivo": f"Data '{data}' inválida; use o formato AAAA-MM-DD."}


def linha_de_hoje() -> str:
    hoje = date.today()
    return f"Hoje é {DIAS_DA_SEMANA[hoje.weekday()]}, {hoje.isoformat()}."
