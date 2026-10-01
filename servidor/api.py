from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from autenticacao import ErroAutenticacao
from banco import CAMINHO_BANCO_PADRAO, fechar_conexao, inicializar_banco
from rotas_sessoes import rotas_sessoes
from rotas_usuarios import ErroRequisicao, rotas_usuarios
from validacao import ErroValidacao

PREFIXO = "/api/v1"

CABECALHOS_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

MENSAGENS_ERRO = {
    400: "Requisição inválida.",
    404: "Recurso não encontrado.",
    405: "Método não permitido para este recurso.",
}


def criar_api(log, caminho_banco=CAMINHO_BANCO_PADRAO):
    app = Flask(__name__)
    app.config["CAMINHO_BANCO"] = caminho_banco
    app.json.ensure_ascii = False
    app.url_map.merge_slashes = False

    inicializar_banco(caminho_banco)
    app.register_blueprint(rotas_usuarios, url_prefix=PREFIXO)
    app.register_blueprint(rotas_sessoes, url_prefix=PREFIXO)
    app.teardown_appcontext(fechar_conexao)

    @app.before_request
    def responder_preflight():
        if request.method == "OPTIONS":
            return app.response_class(status=204)
        return None

    @app.after_request
    def finalizar_resposta(resposta):
        if resposta.status_code == 204:
            resposta.headers.pop("Content-Type", None)
        resposta.headers.update(CABECALHOS_CORS)
        log.registrar(request.remote_addr, request.method, request.path, resposta.status_code)
        return resposta

    @app.errorhandler(ErroValidacao)
    def tratar_erro_validacao(erro):
        return jsonify(mensagem=str(erro)), 400

    @app.errorhandler(ErroAutenticacao)
    def tratar_erro_autenticacao(_erro):
        return jsonify(mensagem="Token ausente ou inválido."), 401

    @app.errorhandler(ErroRequisicao)
    def tratar_erro_requisicao(erro):
        return jsonify(mensagem=erro.mensagem), erro.status

    @app.errorhandler(HTTPException)
    def tratar_erro_http(erro):
        mensagem = MENSAGENS_ERRO.get(erro.code, erro.name)
        resposta = jsonify(mensagem=mensagem)
        resposta.status_code = erro.code
        if erro.code == 405 and getattr(erro, "valid_methods", None):
            resposta.headers["Allow"] = ", ".join(erro.valid_methods)
        return resposta

    @app.errorhandler(Exception)
    def tratar_erro_inesperado(erro):
        app.logger.exception("Erro inesperado: %s", erro)
        return jsonify(mensagem="Erro interno do servidor."), 500

    return app
