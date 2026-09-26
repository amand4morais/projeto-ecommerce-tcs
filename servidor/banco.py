import os
import sqlite3
from contextlib import closing

CAMINHO_BANCO_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- impede reaproveitar id de usuário excluído
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    senha_hash  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    token_hash  TEXT NOT NULL UNIQUE,
    usuario_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    criado_em   TEXT NOT NULL
);
"""


def conectar(caminho_banco):
    conexao = sqlite3.connect(caminho_banco, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def inicializar_banco(caminho_banco):
    with closing(conectar(caminho_banco)) as conexao:
        conexao.executescript(ESQUEMA)
        conexao.commit()
