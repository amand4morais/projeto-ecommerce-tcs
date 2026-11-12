import os
import sqlite3
from contextlib import closing

from flask import current_app, g
from werkzeug.security import generate_password_hash

CAMINHO_BANCO_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db")

ADM_PADRAO = {"nome": "Admin", "email": "adm@teste.com", "senha": "admin123"}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- impede reaproveitar id de usuário excluído
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    senha_hash  TEXT NOT NULL,
    admin       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    token_hash  TEXT NOT NULL UNIQUE,
    usuario_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    criado_em   TEXT NOT NULL,
    ip          TEXT NOT NULL
);
"""


COLUNAS_OBRIGATORIAS = {"users": {"admin"}, "sessions": {"ip"}}


class BancoDesatualizado(ValueError):
    pass


def conectar(caminho_banco):
    conexao = sqlite3.connect(caminho_banco, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def verificar_esquema(conexao):
    for tabela, colunas in COLUNAS_OBRIGATORIAS.items():
        existentes = {linha["name"] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}
        if not colunas <= existentes:
            raise BancoDesatualizado(
                "Banco de dados de versão anterior. Apague servidor/ecommerce.db e inicie novamente."
            )


def garantir_adm_padrao(conexao):
    existe = conexao.execute("SELECT 1 FROM users WHERE email = ?", (ADM_PADRAO["email"],)).fetchone()
    if existe is None:
        conexao.execute(
            "INSERT INTO users (nome, email, senha_hash, admin) VALUES (?, ?, ?, 1)",
            (ADM_PADRAO["nome"], ADM_PADRAO["email"], generate_password_hash(ADM_PADRAO["senha"])),
        )


def inicializar_banco(caminho_banco):
    with closing(conectar(caminho_banco)) as conexao:
        conexao.executescript(ESQUEMA)
        verificar_esquema(conexao)
        with conexao:
            garantir_adm_padrao(conexao)


def obter_conexao():
    if "conexao" not in g:
        g.conexao = conectar(current_app.config["CAMINHO_BANCO"])
    return g.conexao


def fechar_conexao(_erro=None):
    conexao = g.pop("conexao", None)
    if conexao is not None:
        conexao.close()
