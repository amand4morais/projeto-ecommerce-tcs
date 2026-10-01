import sqlite3

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from autenticacao import usuario_autenticado
from banco import obter_conexao
from validacao import (
    ler_objeto_json,
    validar_id_usuario,
    validar_usuario_completo,
    validar_usuario_parcial,
)

rotas_usuarios = Blueprint("usuarios", __name__)

COLUNAS_ATUALIZAVEIS = {"nome": "nome", "email": "email", "senha": "senha_hash"}


class ErroRequisicao(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


def dados_publicos(usuario):
    return {"id": usuario["id"], "nome": usuario["nome"], "email": usuario["email"]}


def buscar_usuario_do_dono(id_texto):
    usuario_id = usuario_autenticado()
    id_url = validar_id_usuario(id_texto)
    if id_url != usuario_id:
        raise ErroRequisicao(403, "Você só pode acessar o seu próprio cadastro.")
    usuario = obter_conexao().execute("SELECT id, nome, email FROM users WHERE id = ?", (id_url,)).fetchone()
    if usuario is None:
        raise ErroRequisicao(404, "Usuário não encontrado.")
    return usuario


def atualizar_usuario(usuario_id, campos):
    valores = {
        COLUNAS_ATUALIZAVEIS[campo]: generate_password_hash(valor) if campo == "senha" else valor
        for campo, valor in campos.items()
    }
    atribuicoes = ", ".join(f"{coluna} = ?" for coluna in valores)
    conexao = obter_conexao()
    try:
        with conexao:
            conexao.execute(f"UPDATE users SET {atribuicoes} WHERE id = ?", (*valores.values(), usuario_id))
    except sqlite3.IntegrityError:
        raise ErroRequisicao(409, "Este e-mail já está em uso por outro usuário.")
    return conexao.execute("SELECT id, nome, email FROM users WHERE id = ?", (usuario_id,)).fetchone()


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


@rotas_usuarios.get("/users/<id_usuario>")
def ler_usuario(id_usuario):
    return jsonify(dados_publicos(buscar_usuario_do_dono(id_usuario)))


@rotas_usuarios.put("/users/<id_usuario>")
def substituir_usuario(id_usuario):
    usuario = buscar_usuario_do_dono(id_usuario)
    campos = validar_usuario_completo(ler_objeto_json(request))
    return jsonify(dados_publicos(atualizar_usuario(usuario["id"], campos)))


@rotas_usuarios.patch("/users/<id_usuario>")
def alterar_usuario(id_usuario):
    usuario = buscar_usuario_do_dono(id_usuario)
    campos = validar_usuario_parcial(ler_objeto_json(request))
    return jsonify(dados_publicos(atualizar_usuario(usuario["id"], campos)))


@rotas_usuarios.delete("/users/<id_usuario>")
def excluir_usuario(id_usuario):
    usuario = buscar_usuario_do_dono(id_usuario)
    conexao = obter_conexao()
    with conexao:
        conexao.execute("DELETE FROM users WHERE id = ?", (usuario["id"],))
    return "", 204
