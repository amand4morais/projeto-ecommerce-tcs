import hashlib

from flask import request

from banco import obter_conexao


class ErroAutenticacao(Exception):
    pass


def calcular_hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def usuario_autenticado():
    esquema, _, token = request.headers.get("Authorization", "").partition(" ")
    if esquema.lower() != "bearer" or not token:
        raise ErroAutenticacao()
    sessao = obter_conexao().execute(
        "SELECT usuario_id FROM sessions WHERE token_hash = ?", (calcular_hash_token(token),)
    ).fetchone()
    if sessao is None:
        raise ErroAutenticacao()
    return sessao["usuario_id"]
