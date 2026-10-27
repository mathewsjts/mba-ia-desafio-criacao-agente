"""Agente principal do assistente e montagem do App do ADK."""

from google.adk.agents import LlmAgent
from google.adk.apps import App

from aurora import config

INSTRUCAO_PRINCIPAL = """\
Você é o assistente virtual do Residencial Aurora e conversa com um morador
pelo aplicativo do condomínio. Responda sempre em português, de forma breve e cordial.
"""


def criar_agente_principal() -> LlmAgent:
    return LlmAgent(
        name="assistente_aurora",
        model=config.MODELO,
        description="Atende o morador e distribui o trabalho entre os especialistas.",
        instruction=INSTRUCAO_PRINCIPAL,
    )


def criar_app() -> App:
    return App(name=config.APP_NAME, root_agent=criar_agente_principal())
