"""Regulamento interno dividido em capítulos, cada um sobre um único assunto."""

import re
from dataclasses import dataclass
from functools import cache

from aurora import config

CABECALHO = re.compile(r"^## Capítulo (?P<numero>[IVXLC]+): (?P<titulo>.+)$", re.MULTILINE)
ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


@dataclass(frozen=True)
class Capitulo:
    numero: str
    titulo: str
    texto: str


def _romano_para_int(romano: str) -> int:
    valores = [ROMANOS[letra] for letra in romano]
    return sum(-v if v < proximo else v for v, proximo in zip(valores, valores[1:] + [0]))


@cache
def capitulos() -> dict[str, Capitulo]:
    """Capítulos indexados pelo número romano (ex.: "IV")."""
    texto = (config.DADOS / "regulamento.md").read_text(encoding="utf-8")
    cabecalhos = list(CABECALHO.finditer(texto))
    fins = [c.start() for c in cabecalhos[1:]] + [len(texto)]
    return {
        c["numero"]: Capitulo(c["numero"], c["titulo"].strip(), texto[c.start():fim].strip())
        for c, fim in zip(cabecalhos, fins)
    }


def buscar(numero: str) -> Capitulo | None:
    """Aceita o número romano ("IV") ou arábico ("4")."""
    numero = numero.strip().upper().removeprefix("CAPÍTULO").strip()
    if numero.isdigit():
        numero = next(
            (romano for romano in capitulos() if _romano_para_int(romano) == int(numero)), ""
        )
    return capitulos().get(numero)
