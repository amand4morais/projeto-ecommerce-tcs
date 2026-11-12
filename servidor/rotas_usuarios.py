import sqlite3

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from autenticacao import sessao_autenticada
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


CONSULTA_USUARIO = "SELECT id, nome, email, admin FROM users"


def dados_publicos(usuario):
    return {"id": usuario["id"], "nome": usuario["nome"], "email": usuario["email"], "admin": bool(usuario["admin"])}


def buscar_usuario_permitido(id_texto):
    sessao = sessao_autenticada()
    id_url = validar_id_usuario(id_texto)
    if id_url != sessao["usuario_id"] and not sessao["admin"]:
        raise ErroRequisicao(403, "Você só pode acessar o seu próprio cadastro.")
    usuario = obter_conexao().execute(f"{CONSULTA_USUARIO} WHERE id = ?", (id_url,)).fetchone()
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
    return conexao.execute(f"{CONSULTA_USUARIO} WHERE id = ?", (usuario_id,)).fetchone()


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
    resposta = jsonify(id=cursor.lastrowid, nome=usuario["nome"], email=usuario["email"], admin=False)
    resposta.headers["Location"] = f"/api/v1/users/{cursor.lastrowid}"
    return resposta, 201


@rotas_usuarios.get("/users")
def listar_usuarios():
    if not sessao_autenticada()["admin"]:
        raise ErroRequisicao(403, "Somente administradores podem listar os usuários.")
    usuarios = obter_conexao().execute(f"{CONSULTA_USUARIO} ORDER BY id").fetchall()
    return jsonify([dados_publicos(usuario) for usuario in usuarios])


@rotas_usuarios.get("/users/<id_usuario>")
def ler_usuario(id_usuario):
    return jsonify(dados_publicos(buscar_usuario_permitido(id_usuario)))


@rotas_usuarios.put("/users/<id_usuario>")
def substituir_usuario(id_usuario):
    usuario = buscar_usuario_permitido(id_usuario)
    campos = validar_usuario_completo(ler_objeto_json(request))
    return jsonify(dados_publicos(atualizar_usuario(usuario["id"], campos)))


@rotas_usuarios.patch("/users/<id_usuario>")
def alterar_usuario(id_usuario):
    usuario = buscar_usuario_permitido(id_usuario)
    campos = validar_usuario_parcial(ler_objeto_json(request))
    return jsonify(dados_publicos(atualizar_usuario(usuario["id"], campos)))


@rotas_usuarios.delete("/users/<id_usuario>")
def excluir_usuario(id_usuario):
    usuario = buscar_usuario_permitido(id_usuario)
    conexao = obter_conexao()
    with conexao:
        conexao.execute("DELETE FROM users WHERE id = ?", (usuario["id"],))
    return "", 204
