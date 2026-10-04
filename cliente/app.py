from flask import Flask, jsonify, render_template, request

from encaminhador import (
    ErroEnvio,
    encaminhar,
    validar_caminho,
    validar_host,
    validar_metodo,
    validar_porta,
)


def criar_cliente():
    app = Flask(__name__)
    app.json.ensure_ascii = False

    @app.before_request
    def exigir_json_em_post():
        # Proteção contra CSRF: outro site não consegue enviar JSON para cá sem preflight.
        if request.method == "POST" and not request.is_json:
            return jsonify(mensagem="Envie os dados em JSON."), 415
        return None

    @app.get("/")
    def pagina():
        return render_template("index.html")

    @app.post("/enviar")
    def enviar():
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            return jsonify(mensagem="Requisição inválida."), 400
        try:
            destino = {
                "host": validar_host(dados.get("host")),
                "porta": validar_porta(dados.get("porta")),
                "metodo": validar_metodo(dados.get("metodo")),
                "caminho": validar_caminho(dados.get("caminho")),
            }
        except ValueError as erro:
            return jsonify(mensagem=str(erro)), 400
        token = dados.get("token") if isinstance(dados.get("token"), str) else None
        try:
            return jsonify(encaminhar(**destino, corpo=dados.get("corpo"), token=token))
        except ErroEnvio as erro:
            return jsonify(mensagem=str(erro)), 502

    return app
