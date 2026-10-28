"""Especialista de reservas das áreas comuns."""

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool, ToolContext

from aurora import condominio, config
from aurora.agentes._comum import (
    apartamento_da_sessao,
    aprovada_pelo_morador,
    data_invalida,
    linha_de_hoje,
)


def _area_invalida(area: str) -> dict | None:
    if condominio.buscar_area(area):
        return None
    ids = ", ".join(a["id"] for a in condominio.listar_areas())
    return {"status": "invalido", "motivo": f"Área '{area}' não existe. Áreas: {ids}."}


def listar_minhas_reservas(tool_context: ToolContext) -> dict:
    """Lista as reservas ativas do apartamento do morador."""
    return {"reservas": condominio.listar_reservas(apartamento_da_sessao(tool_context))}


def verificar_disponibilidade(area: str, data: str) -> dict:
    """Informa se uma área comum está livre ou ocupada numa data.

    Args:
        area: id da área comum (ex.: salao-de-festas).
        data: data no formato AAAA-MM-DD.
    """
    if erro := _area_invalida(area) or data_invalida(data):
        return erro
    # Só livre/ocupada: nunca de quem é a reserva (Garantia 2).
    return {"area": area, "data": data,
            "disponibilidade": "livre" if condominio.area_livre(area, data) else "ocupada"}


def _gera_cobranca(area: str, data: str, **_) -> bool:
    """Garantia 1: reservar área com taxa pede confirmação, decidida aqui e não pelo modelo.

    Área ou data inválida, ou data já ocupada, não pede confirmação: nesses casos o corpo de
    `reservar_area` não grava nada sem aprovação. O ADK reavalia esta função na retomada.
    """
    dados_area = condominio.buscar_area(area)
    return (
        dados_area is not None
        and dados_area["taxa"] > 0
        and data_invalida(data) is None
        and condominio.area_livre(area, data)
    )


def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
    """Reserva uma área comum para o apartamento do morador numa data.

    Áreas com taxa geram cobrança e ficam pendentes até o morador aprovar pelo aplicativo.

    Args:
        area: id da área comum (ex.: salao-de-festas).
        data: data no formato AAAA-MM-DD.
    """
    if erro := _area_invalida(area) or data_invalida(data):
        return erro
    taxa = condominio.buscar_area(area)["taxa"]
    if taxa > 0 and not aprovada_pelo_morador(tool_context):
        # Sem aprovação só se chega aqui quando _gera_cobranca viu a data ocupada (ou o
        # morador negou e a data foi ocupada antes da retomada): nada é gravado.
        return {"status": "indisponivel", "area": area, "data": data}
    codigo = condominio.reservar(apartamento_da_sessao(tool_context), area, data)
    if codigo is None:
        return {"status": "indisponivel", "area": area, "data": data}
    return {"status": "reservada", "codigo": codigo, "area": area, "data": data,
            "cobranca": taxa > 0, "taxa": taxa}


def cancelar_reserva(area: str, data: str, tool_context: ToolContext) -> dict:
    """Cancela uma reserva ativa do apartamento do morador.

    Args:
        area: id da área comum (ex.: quadra).
        data: data da reserva no formato AAAA-MM-DD.
    """
    if erro := _area_invalida(area) or data_invalida(data):
        return erro
    codigo = condominio.cancelar(apartamento_da_sessao(tool_context), area, data)
    if codigo is None:
        return {"status": "nao_encontrada",
                "motivo": "Você não tem reserva dessa área nessa data."}
    return {"status": "cancelada", "codigo": codigo, "area": area, "data": data}


def _instrucao(_: ReadonlyContext) -> str:
    areas = "\n".join(
        f"- {a['id']}: {a['nome']}, taxa R$ {a['taxa']:.2f}" for a in condominio.listar_areas()
    )
    return f"""\
Você é o especialista em reservas das áreas comuns do Residencial Aurora.
{linha_de_hoje()} Converta datas relativas para AAAA-MM-DD antes de chamar as tools.

Áreas comuns (use sempre o id nas tools):
{areas}

Regras:
- Use as tools para ler e gravar reservas; nunca invente reservas, códigos ou disponibilidade.
- Você só enxerga e altera reservas do apartamento do morador atendido. Se o pedido
  mencionar outro apartamento, diga que só pode tratar das reservas do próprio apartamento.
- Antes de chamar reservar_area, verifique a disponibilidade da área na data com
  verificar_disponibilidade. Se estiver ocupada, não chame reservar_area.
- Quando uma data está ocupada, diga apenas que ela está indisponível, sem especular de quem é.
- Para cancelar, use cancelar_reserva com a área e a data; se ela retornar nao_encontrada,
  diga ao morador: "você não tem reserva dessa área nessa data".
- Só diga que uma reserva foi feita ou cancelada quando a tool retornar esse status.
- Quando reservar_area retorna status reservada, a reserva já está gravada; se houve cobrança,
  o morador já aprovou a taxa pelo aplicativo. Informe o código e a taxa, sem dizer que falta aprovar.
- Responda em português, de forma breve, com o resultado do que foi feito.
"""


def criar_especialista_reservas() -> LlmAgent:
    return LlmAgent(
        name="reservas",
        model=config.MODELO,
        mode="single_turn",
        description=(
            "Consulta, verifica disponibilidade, cria e cancela reservas do salão de festas, "
            "da churrasqueira e da quadra para o apartamento do morador."
        ),
        instruction=_instrucao,
        tools=[
            listar_minhas_reservas,
            verificar_disponibilidade,
            FunctionTool(reservar_area, require_confirmation=_gera_cobranca),
            cancelar_reserva,
        ],
    )
