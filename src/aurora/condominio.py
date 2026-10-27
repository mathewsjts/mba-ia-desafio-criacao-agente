"""Dados do condomínio em SQLite: apartamentos, áreas, reservas e autorizações de visita.

Todas as funções que leem ou gravam dados de um apartamento recebem o número dele
explicitamente; quem chama (as tools) obtém esse número do state da sessão.
"""

import json
import secrets
import sqlite3
import string
from contextlib import closing
from pathlib import Path

from aurora import config

ESQUEMA = """
CREATE TABLE apartamentos (
    numero TEXT PRIMARY KEY,
    morador TEXT NOT NULL
);
CREATE TABLE areas (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    taxa REAL NOT NULL
);
CREATE TABLE reservas (
    codigo TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL REFERENCES apartamentos(numero),
    area TEXT NOT NULL REFERENCES areas(id),
    data TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'cancelada'))
);
-- Garantia 5: no máximo uma reserva ativa por área e data, verificada no INSERT.
CREATE UNIQUE INDEX reserva_ativa_unica ON reservas(area, data) WHERE status = 'ativa';
CREATE TABLE autorizacoes_visita (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartamento TEXT NOT NULL REFERENCES apartamentos(numero),
    nome TEXT NOT NULL,
    data TEXT NOT NULL,
    UNIQUE (apartamento, nome, data)
);
"""

ALFABETO_CODIGO = string.ascii_uppercase + string.digits


def _conectar(caminho: Path | None = None) -> sqlite3.Connection:
    conexao = sqlite3.connect(caminho or config.CONDOMINIO_DB, timeout=30)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def _ler_json(nome: str) -> list[dict]:
    return json.loads((config.DADOS / nome).read_text(encoding="utf-8"))


def criar_banco(caminho: Path | None = None) -> None:
    """Cria o esquema e carrega o estado inicial de `dados/`."""
    caminho = caminho or config.CONDOMINIO_DB
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with closing(_conectar(caminho)) as conexao, conexao:
        conexao.execute("PRAGMA journal_mode = WAL")
        conexao.executescript(ESQUEMA)
        conexao.executemany(
            "INSERT INTO apartamentos (numero, morador) VALUES (:numero, :morador)",
            _ler_json("apartamentos.json"),
        )
        conexao.executemany(
            "INSERT INTO areas (id, nome, taxa) VALUES (:id, :nome, :taxa)",
            _ler_json("areas.json"),
        )
        conexao.executemany(
            "INSERT INTO reservas (codigo, apartamento, area, data) "
            "VALUES (:codigo, :apartamento, :area, :data)",
            _ler_json("reservas.json"),
        )
        conexao.executemany(
            "INSERT INTO autorizacoes_visita (apartamento, nome, data) "
            "VALUES (:apartamento, :nome, :data)",
            _ler_json("visitantes.json"),
        )


def garantir_banco() -> None:
    """Cria o banco só se ele ainda não existe; nunca reseta um banco existente."""
    if not config.CONDOMINIO_DB.exists():
        criar_banco()


def apartamento_existe(numero: str) -> bool:
    with closing(_conectar()) as conexao:
        linha = conexao.execute(
            "SELECT 1 FROM apartamentos WHERE numero = ?", (numero,)
        ).fetchone()
    return linha is not None


def listar_areas() -> list[dict]:
    with closing(_conectar()) as conexao:
        linhas = conexao.execute("SELECT id, nome, taxa FROM areas ORDER BY id").fetchall()
    return [dict(linha) for linha in linhas]


def buscar_area(area: str) -> dict | None:
    with closing(_conectar()) as conexao:
        linha = conexao.execute(
            "SELECT id, nome, taxa FROM areas WHERE id = ?", (area,)
        ).fetchone()
    return dict(linha) if linha else None


def listar_reservas(apartamento: str) -> list[dict]:
    """Reservas ativas do apartamento."""
    with closing(_conectar()) as conexao:
        linhas = conexao.execute(
            "SELECT codigo, area, data FROM reservas "
            "WHERE apartamento = ? AND status = 'ativa' ORDER BY data, area",
            (apartamento,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def area_livre(area: str, data: str) -> bool:
    """Só diz se a data está livre; nunca de quem é a reserva."""
    with closing(_conectar()) as conexao:
        linha = conexao.execute(
            "SELECT 1 FROM reservas WHERE area = ? AND data = ? AND status = 'ativa'",
            (area, data),
        ).fetchone()
    return linha is None


def _novo_codigo() -> str:
    return "RSV-" + "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(6))


def reservar(apartamento: str, area: str, data: str) -> str | None:
    """Grava a reserva e devolve o código, ou None se a área já está ocupada na data.

    A exclusividade vem do índice `reserva_ativa_unica`, no instante do INSERT:
    duas gravações simultâneas não passam juntas, mesmo que ambas tenham visto a data livre.
    """
    with closing(_conectar()) as conexao:
        while True:
            codigo = _novo_codigo()
            try:
                with conexao:
                    conexao.execute(
                        "INSERT INTO reservas (codigo, apartamento, area, data) "
                        "VALUES (?, ?, ?, ?)",
                        (codigo, apartamento, area, data),
                    )
                return codigo
            except sqlite3.IntegrityError as erro:
                if "reservas.codigo" in str(erro):
                    continue  # código já usado, inclusive por reserva cancelada
                return None


def cancelar(apartamento: str, area: str, data: str) -> str | None:
    """Cancela a reserva ativa do próprio apartamento e devolve o código, ou None."""
    with closing(_conectar()) as conexao, conexao:
        linha = conexao.execute(
            "UPDATE reservas SET status = 'cancelada' "
            "WHERE apartamento = ? AND area = ? AND data = ? AND status = 'ativa' "
            "RETURNING codigo",
            (apartamento, area, data),
        ).fetchone()
    return linha["codigo"] if linha else None


def listar_autorizacoes(apartamento: str) -> list[dict]:
    with closing(_conectar()) as conexao:
        linhas = conexao.execute(
            "SELECT nome, data FROM autorizacoes_visita "
            "WHERE apartamento = ? ORDER BY data, nome",
            (apartamento,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def autorizar_visita(apartamento: str, nome: str, data: str) -> bool:
    """Grava a autorização de visita; devolve False se ela já existia."""
    with closing(_conectar()) as conexao, conexao:
        cursor = conexao.execute(
            "INSERT OR IGNORE INTO autorizacoes_visita (apartamento, nome, data) "
            "VALUES (?, ?, ?)",
            (apartamento, nome, data),
        )
    return cursor.rowcount == 1
