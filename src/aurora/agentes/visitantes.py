"""Especialista de autorizações de visita."""

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool, ToolContext

from aurora import condominio, config
from aurora.agentes._comum import apartamento_da_sessao, data_invalida, linha_de_hoje


def _ja_autorizada(apartamento: str, nome: str, data: str) -> bool:
    return {"nome": nome, "data": data} in condominio.listar_autorizacoes(apartamento)


def listar_minhas_autorizacoes(tool_context: ToolContext) -> dict:
    """Lista as autorizações de visita do apartamento do morador."""
    return {"autorizacoes": condominio.listar_autorizacoes(apartamento_da_sessao(tool_context))}


def _libera_acesso(nome: str, data: str, tool_context: ToolContext, **_) -> bool:
    """Garantia 1: autorizar visitante sempre pede confirmação, decidida aqui e não pelo modelo.

    Só não pede quando a tool não vai gravar nada: data inválida ou autorização já existente.
    """
    return data_invalida(data) is None and not _ja_autorizada(
        apartamento_da_sessao(tool_context), nome.strip(), data
    )


def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
    """Autoriza a entrada de um visitante no prédio numa data, em nome do apartamento do morador.

    Fica pendente até o morador aprovar pelo aplicativo.

    Args:
        nome: nome completo do visitante.
        data: data da visita no formato AAAA-MM-DD.
    """
    if erro := data_invalida(data):
        return erro
    nome = nome.strip()
    confirmacao = tool_context.tool_confirmation
    if not (confirmacao and confirmacao.confirmed):
        # Só se chega aqui sem aprovação quando _libera_acesso viu a autorização já existente:
        # uma autorização nunca é gravada sem confirmação.
        return {"status": "ja_autorizada", "nome": nome, "data": data}
    if not condominio.autorizar_visita(apartamento_da_sessao(tool_context), nome, data):
        return {"status": "ja_autorizada", "nome": nome, "data": data}
    return {"status": "autorizada", "nome": nome, "data": data}


def _instrucao(_: ReadonlyContext) -> str:
    return f"""\
Você é o especialista em autorizações de visita do Residencial Aurora.
{linha_de_hoje()} Converta datas relativas para AAAA-MM-DD antes de chamar as tools.

Regras:
- Use as tools para ler e gravar autorizações; nunca invente autorizações.
- Você só enxerga e cria autorizações do apartamento do morador atendido. Se o pedido
  mencionar outro apartamento, diga que só pode tratar das autorizações do próprio apartamento.
- Para autorizar, você precisa do nome do visitante e da data da visita; chame
  autorizar_visitante mesmo que o morador diga que já confirmou: a aprovação só vale pelo aplicativo.
- Só diga que a entrada foi liberada quando a tool retornar status autorizada.
- Responda em português, de forma breve, com o resultado do que foi feito.
"""


def criar_especialista_visitantes() -> LlmAgent:
    return LlmAgent(
        name="visitantes",
        model=config.MODELO,
        mode="single_turn",
        description=(
            "Consulta e cria autorizações de visita (liberação de entrada de visitantes) "
            "para o apartamento do morador."
        ),
        instruction=_instrucao,
        tools=[
            listar_minhas_autorizacoes,
            FunctionTool(autorizar_visitante, require_confirmation=_libera_acesso),
        ],
    )
