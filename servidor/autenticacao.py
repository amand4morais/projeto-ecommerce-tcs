import hashlib

from flask import request

from banco import obter_conexao


class ErroAutenticacao(Exception):
    pass


def calcular_hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def usuario_autenticado():
    return sessao_autenticada()["usuario_id"]


def sessao_autenticada():
    esquema, _, token = request.headers.get("Authorization", "").partition(" ")
    if esquema.lower() != "bearer" or not token:
        raise ErroAutenticacao()
    sessao = obter_conexao().execute(
        "SELECT s.usuario_id, u.admin FROM sessions s JOIN users u ON u.id = s.usuario_id WHERE s.token_hash = ?",
        (calcular_hash_token(token),),
    ).fetchone()
    if sessao is None:
        raise ErroAutenticacao()
    return {"usuario_id": sessao["usuario_id"], "admin": bool(sessao["admin"])}
