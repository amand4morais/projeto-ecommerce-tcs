import secrets
import sqlite3
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from autenticacao import calcular_hash_token, usuario_autenticado
from banco import obter_conexao
from validacao import ler_objeto_json, validar_login

rotas_sessoes = Blueprint("sessoes", __name__)

MENSAGEM_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos."

# Conferido quando o e-mail não existe, para o tempo de resposta não revelar quais e-mails estão cadastrados.
HASH_FICTICIO = generate_password_hash("SenhaInexistente0")


@rotas_sessoes.post("/sessions")
def criar_sessao():
    credenciais = validar_login(ler_objeto_json(request))
    conexao = obter_conexao()
    usuario = conexao.execute(
        "SELECT id, nome, email, senha_hash FROM users WHERE email = ?", (credenciais["email"],)
    ).fetchone()
    senha_correta = check_password_hash(usuario["senha_hash"] if usuario else HASH_FICTICIO, credenciais["senha"])
    if usuario is None or not senha_correta:
        return jsonify(mensagem=MENSAGEM_CREDENCIAIS_INVALIDAS), 401

    id_sessao = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    try:
        with conexao:
            conexao.execute(
                "INSERT INTO sessions (id, token_hash, usuario_id, criado_em) VALUES (?, ?, ?, ?)",
                (id_sessao, calcular_hash_token(token), usuario["id"], datetime.now(timezone.utc).isoformat()),
            )
    except sqlite3.IntegrityError:
        return jsonify(mensagem=MENSAGEM_CREDENCIAIS_INVALIDAS), 401

    return jsonify(
        id=id_sessao,
        token=token,
        usuario={"id": usuario["id"], "nome": usuario["nome"], "email": usuario["email"]},
    ), 201


@rotas_sessoes.delete("/sessions/<id_sessao>")
def encerrar_sessao(id_sessao):
    usuario_id = usuario_autenticado()
    conexao = obter_conexao()
    sessao = conexao.execute("SELECT usuario_id FROM sessions WHERE id = ?", (id_sessao,)).fetchone()
    if sessao is None:
        return jsonify(mensagem="Sessão não encontrada."), 404
    if sessao["usuario_id"] != usuario_id:
        return jsonify(mensagem="Esta sessão pertence a outro usuário."), 403
    with conexao:
        conexao.execute("DELETE FROM sessions WHERE id = ?", (id_sessao,))
    return "", 204
