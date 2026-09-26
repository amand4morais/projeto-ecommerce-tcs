from flask import Flask, jsonify, render_template, request


def criar_painel(controle, log):
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
        return render_template("painel.html")

    @app.get("/estado")
    def estado():
        return jsonify(controle.estado())

    @app.post("/iniciar")
    def iniciar():
        dados = request.get_json(silent=True) or {}
        try:
            porta = controle.iniciar(dados.get("porta", ""))
        except ValueError as erro:
            return jsonify(mensagem=str(erro)), 400
        return jsonify(mensagem=f"API rodando na porta {porta}.", **controle.estado())

    @app.post("/parar")
    def parar():
        try:
            controle.parar()
        except ValueError as erro:
            return jsonify(mensagem=str(erro)), 400
        return jsonify(mensagem="API parada.", **controle.estado())

    @app.get("/log")
    def ler_log():
        desde = request.args.get("desde", "0")
        desde_id = int(desde) if desde.isdigit() else 0
        return jsonify(log.listar(desde_id))

    return app
