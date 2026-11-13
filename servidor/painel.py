import os
import socket
import sqlite3
from contextlib import closing

from flask import Flask, jsonify, render_template, request

from banco import CAMINHO_BANCO_PADRAO

CONSULTA_USUARIOS_LOGADOS = """
SELECT u.id, u.nome, u.email, u.admin,
       COUNT(s.id) AS sessoes,
       MAX(s.criado_em) AS ultimo_login,
       (SELECT s2.ip FROM sessions s2 WHERE s2.usuario_id = u.id ORDER BY s2.criado_em DESC LIMIT 1) AS ip
FROM users u
JOIN sessions s ON s.usuario_id = u.id
GROUP BY u.id
ORDER BY ultimo_login DESC
"""


def ler_usuarios_logados(caminho_banco):
    if not os.path.exists(caminho_banco):
        return []
    with closing(sqlite3.connect(caminho_banco, timeout=10)) as conexao:
        conexao.row_factory = sqlite3.Row
        return [
            {
                "id": linha["id"],
                "nome": linha["nome"],
                "email": linha["email"],
                "admin": bool(linha["admin"]),
                "sessoes": linha["sessoes"],
                "ultimo_login": linha["ultimo_login"],
                "ip": linha["ip"],
            }
            for linha in conexao.execute(CONSULTA_USUARIOS_LOGADOS)
        ]


def enderecos_locais():
    enderecos = set()
    try:
        # Conectar um socket UDP não envia pacotes; só revela o IP da interface de rede principal.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as teste:
            teste.connect(("10.255.255.255", 1))
            enderecos.add(teste.getsockname()[0])
    except OSError:
        pass
    try:
        enderecos.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return sorted(ip for ip in enderecos if not ip.startswith("127."))


def criar_painel(controle, log, caminho_banco=CAMINHO_BANCO_PADRAO):
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
        return render_template("painel.html", pagina="visao-geral")

    @app.get("/comunicacao")
    def pagina_comunicacao():
        return render_template("comunicacao.html", pagina="comunicacao")

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
        return jsonify(execucao=log.execucao, registros=log.listar(desde_id))

    @app.get("/usuarios-logados")
    def usuarios_logados():
        try:
            return jsonify(ler_usuarios_logados(caminho_banco))
        except sqlite3.Error:
            return jsonify(mensagem="Não foi possível ler as sessões do banco de dados."), 503

    @app.get("/indicadores")
    def indicadores():
        return jsonify(
            requisicoes=log.total(),
            clientes_ativos=log.clientes_ativos(),
            enderecos=enderecos_locais(),
        )

    return app
