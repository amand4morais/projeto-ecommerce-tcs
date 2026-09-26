from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from banco import CAMINHO_BANCO_PADRAO, inicializar_banco

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

    @app.before_request
    def responder_preflight():
        if request.method == "OPTIONS":
            resposta = app.response_class(status=204)
            resposta.headers.pop("Content-Type", None)
            return resposta
        return None

    @app.after_request
    def finalizar_resposta(resposta):
        resposta.headers.update(CABECALHOS_CORS)
        log.registrar(request.remote_addr, request.method, request.path, resposta.status_code)
        return resposta

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
