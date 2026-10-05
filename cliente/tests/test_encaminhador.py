import json
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import encaminhador
from app import criar_cliente


class ServidorFalso(BaseHTTPRequestHandler):
    recebidas = []

    def log_message(self, *args):
        pass

    def responder(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(tamanho).decode() if tamanho else None
        ServidorFalso.recebidas.append({
            "metodo": self.command,
            "caminho": self.path,
            "authorization": self.headers.get("Authorization"),
            "content_type": self.headers.get("Content-Type"),
            "corpo": json.loads(corpo) if corpo else None,
        })
        if self.path.endswith("/lento"):
            time.sleep(1)
        if self.path.endswith("/html"):
            self.enviar(500, "text/html", b"<h1>Erro</h1>")
        elif self.path.endswith("/vazio"):
            self.send_response(204)
            self.end_headers()
        else:
            self.enviar(201, "application/json", json.dumps({"mensagem": "ok"}).encode())

    def enviar(self, status, tipo, dados):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = responder


def porta_fechada():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestEnviar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = ThreadingHTTPServer(("127.0.0.1", 0), ServidorFalso)
        cls.porta = cls.servidor.server_address[1]
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def setUp(self):
        ServidorFalso.recebidas.clear()
        self.cliente = criar_cliente().test_client()

    def enviar(self, **dados):
        base = {"host": "127.0.0.1", "porta": str(self.porta), "metodo": "GET", "caminho": "/users/1"}
        return self.cliente.post("/enviar", json={**base, **dados})

    def test_pagina(self):
        r = self.cliente.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn('id="host"', r.get_data(as_text=True))
        self.assertIn('id="porta"', r.get_data(as_text=True))

    def test_repassa_metodo_caminho_corpo_e_token(self):
        r = self.enviar(metodo="PATCH", caminho="/users/7", corpo={"nome": "Ana"}, token="abc123")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {
            "url": f"http://127.0.0.1:{self.porta}/api/v1/users/7",
            "status": 201, "corpo": {"mensagem": "ok"}, "texto": None,
        })
        [recebida] = ServidorFalso.recebidas
        self.assertEqual(recebida["metodo"], "PATCH")
        self.assertEqual(recebida["caminho"], "/api/v1/users/7")
        self.assertEqual(recebida["authorization"], "Bearer abc123")
        self.assertEqual(recebida["content_type"], "application/json")
        self.assertEqual(recebida["corpo"], {"nome": "Ana"})

    def test_sem_token_e_sem_corpo(self):
        self.enviar(metodo="DELETE")
        [recebida] = ServidorFalso.recebidas
        self.assertIsNone(recebida["authorization"])
        self.assertIsNone(recebida["corpo"])

    def test_corpo_invalido_e_enviado_como_digitado(self):
        self.enviar(metodo="POST", caminho="/users", corpo={"nome": 123, "email": None})
        self.assertEqual(ServidorFalso.recebidas[0]["corpo"], {"nome": 123, "email": None})

    def test_repassa_options_para_conectar(self):
        r = self.enviar(metodo="OPTIONS", caminho="/users")
        self.assertEqual(r.get_json()["status"], 201)
        [recebida] = ServidorFalso.recebidas
        self.assertEqual((recebida["metodo"], recebida["caminho"], recebida["corpo"]), ("OPTIONS", "/api/v1/users", None))

    def test_resposta_que_nao_e_json(self):
        dados = self.enviar(caminho="/html").get_json()
        self.assertEqual((dados["status"], dados["corpo"], dados["texto"]), (500, None, "<h1>Erro</h1>"))

    def test_resposta_sem_corpo(self):
        dados = self.enviar(caminho="/vazio").get_json()
        self.assertEqual((dados["status"], dados["corpo"], dados["texto"]), (204, None, ""))

    def test_servidor_desligado(self):
        r = self.enviar(porta=str(porta_fechada()))
        self.assertEqual(r.status_code, 502)
        self.assertIn("Não foi possível conectar", r.get_json()["mensagem"])

    def test_servidor_lento(self):
        with mock.patch.object(encaminhador, "TEMPO_LIMITE", 0.3):
            r = self.enviar(caminho="/lento")
        self.assertEqual(r.status_code, 502)
        self.assertIn("não respondeu", r.get_json()["mensagem"])

    def test_destino_invalido(self):
        casos = [
            {"host": ""}, {"host": "1.2.3.4/x"}, {"host": "a b"}, {"host": "user@host"}, {"host": None},
            {"porta": ""}, {"porta": "0"}, {"porta": "70000"}, {"porta": "abc"}, {"porta": True},
            {"metodo": "HEAD"}, {"metodo": "get"},
            {"caminho": "users"}, {"caminho": "/users?x=1"}, {"caminho": "/users#a"}, {"caminho": None},
        ]
        for caso in casos:
            r = self.enviar(**caso)
            self.assertEqual(r.status_code, 400, caso)
            self.assertIn("mensagem", r.get_json())
        self.assertEqual(ServidorFalso.recebidas, [])

    def test_aceita_localhost_e_porta_numerica(self):
        self.assertEqual(self.enviar(host="localhost", porta=self.porta).status_code, 200)

    def test_exige_json(self):
        r = self.cliente.post("/enviar", data="host=1", content_type="application/x-www-form-urlencoded")
        self.assertEqual(r.status_code, 415)
        self.assertEqual(self.cliente.post("/enviar", json=["x"]).status_code, 400)

    def test_ignora_proxy_do_sistema(self):
        self.assertFalse(encaminhador.sessao_http.trust_env)


if __name__ == "__main__":
    unittest.main()
