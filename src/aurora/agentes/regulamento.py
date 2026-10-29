"""Especialista do regulamento interno, exposto ao agente principal como AgentTool.

Garantia 4: o AgentTool roda o especialista numa sessão separada e descartável, então
o capítulo lido por `ler_capitulo` nunca entra nos eventos da sessão do morador; só a
resposta final do especialista volta ao agente principal.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool

from aurora import config, regulamento


def ler_capitulo(numero: str) -> dict:
    """Lê um único capítulo do regulamento interno.

    Args:
        numero: número do capítulo, em romano (ex.: "IV") ou arábico (ex.: "4").
    """
    capitulo = regulamento.buscar(numero)
    if capitulo is None:
        return {"erro": f"Capítulo '{numero}' não existe."}
    return {"capitulo": capitulo.numero, "titulo": capitulo.titulo, "texto": capitulo.texto}


def _instrucao() -> str:
    indice = "\n".join(
        f"- Capítulo {c.numero}: {c.titulo}" for c in regulamento.capitulos().values()
    )
    return f"""\
Você é o especialista no regulamento interno do Residencial Aurora.
Responda dúvidas apenas com base no regulamento, lendo o capítulo do assunto com ler_capitulo
antes de responder. Leia só o(s) capítulo(s) necessário(s).

Índice do regulamento:
{indice}

Responda em português, de forma objetiva, só sobre o que foi perguntado, citando o artigo
usado. Não transcreva trechos que não respondem à pergunta. Se o regulamento não tratar do
assunto, diga isso.
"""


def criar_especialista_regulamento() -> AgentTool:
    return AgentTool(
        LlmAgent(
            name="regulamento",
            model=config.MODELO,
            description="Responde dúvidas sobre o regulamento interno do condomínio.",
            instruction=_instrucao(),
            tools=[ler_capitulo],
        )
    )
