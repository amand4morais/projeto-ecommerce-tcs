from flask import Blueprint, jsonify, request

from autenticacao import sessao_autenticada
from banco import obter_conexao
from rotas_usuarios import ErroRequisicao
from validacao import ler_objeto_json, validar_id_produto, validar_produto_completo, validar_produto_parcial

rotas_produtos = Blueprint("produtos", __name__)

CONSULTA_PRODUTO = "SELECT id, nome, descricao, quantidade FROM products"


def dados_produto(produto):
    return {
        "id": produto["id"],
        "nome": produto["nome"],
        "descricao": produto["descricao"],
        "quantidade": produto["quantidade"],
    }


def exigir_admin(sessao):
    if not sessao["admin"]:
        raise ErroRequisicao(403, "Somente administradores podem alterar produtos.")


def buscar_produto(id_produto):
    produto = obter_conexao().execute(f"{CONSULTA_PRODUTO} WHERE id = ?", (id_produto,)).fetchone()
    if produto is None:
        raise ErroRequisicao(404, "Produto não encontrado.")
    return produto


def buscar_produto_para_alterar(id_texto):
    sessao = sessao_autenticada()
    id_produto = validar_id_produto(id_texto)
    exigir_admin(sessao)
    return buscar_produto(id_produto)


def atualizar_produto(id_produto, campos):
    atribuicoes = ", ".join(f"{coluna} = ?" for coluna in campos)
    conexao = obter_conexao()
    with conexao:
        conexao.execute(f"UPDATE products SET {atribuicoes} WHERE id = ?", (*campos.values(), id_produto))
    return buscar_produto(id_produto)


@rotas_produtos.get("/products")
def listar_produtos():
    sessao_autenticada()
    produtos = obter_conexao().execute(f"{CONSULTA_PRODUTO} ORDER BY id").fetchall()
    return jsonify([dados_produto(produto) for produto in produtos])


@rotas_produtos.post("/products")
def cadastrar_produto():
    exigir_admin(sessao_autenticada())
    produto = validar_produto_completo(ler_objeto_json(request))
    conexao = obter_conexao()
    with conexao:
        cursor = conexao.execute(
            "INSERT INTO products (nome, descricao, quantidade) VALUES (?, ?, ?)",
            (produto["nome"], produto["descricao"], produto["quantidade"]),
        )
    resposta = jsonify(id=cursor.lastrowid, **produto)
    resposta.headers["Location"] = f"/api/v1/products/{cursor.lastrowid}"
    return resposta, 201


@rotas_produtos.get("/products/<id_produto>")
def ler_produto(id_produto):
    sessao_autenticada()
    return jsonify(dados_produto(buscar_produto(validar_id_produto(id_produto))))


@rotas_produtos.put("/products/<id_produto>")
def substituir_produto(id_produto):
    produto = buscar_produto_para_alterar(id_produto)
    campos = validar_produto_completo(ler_objeto_json(request))
    return jsonify(dados_produto(atualizar_produto(produto["id"], campos)))


@rotas_produtos.patch("/products/<id_produto>")
def alterar_produto(id_produto):
    produto = buscar_produto_para_alterar(id_produto)
    campos = validar_produto_parcial(ler_objeto_json(request))
    return jsonify(dados_produto(atualizar_produto(produto["id"], campos)))


@rotas_produtos.delete("/products/<id_produto>")
def excluir_produto(id_produto):
    produto = buscar_produto_para_alterar(id_produto)
    conexao = obter_conexao()
    with conexao:
        conexao.execute("DELETE FROM products WHERE id = ?", (produto["id"],))
    return "", 204
