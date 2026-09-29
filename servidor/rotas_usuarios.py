import sqlite3

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from banco import obter_conexao
from validacao import ler_objeto_json, validar_usuario_completo

rotas_usuarios = Blueprint("usuarios", __name__)


@rotas_usuarios.post("/users")
def cadastrar_usuario():
    usuario = validar_usuario_completo(ler_objeto_json(request))
    conexao = obter_conexao()
    try:
        with conexao:
            cursor = conexao.execute(
                "INSERT INTO users (nome, email, senha_hash) VALUES (?, ?, ?)",
                (usuario["nome"], usuario["email"], generate_password_hash(usuario["senha"])),
            )
    except sqlite3.IntegrityError:
        return jsonify(mensagem="Este e-mail já está cadastrado. Faça login."), 409
    return jsonify(id=cursor.lastrowid, nome=usuario["nome"], email=usuario["email"]), 201
