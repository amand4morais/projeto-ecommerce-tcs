import os
import socket
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager

import requests

from api import CABECALHOS_CORS, criar_api
from controle_api import ControleAPI, validar_porta
from log_requisicoes import LogRequisicoes
from painel import criar_painel


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class BaseComBanco(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho_banco = os.path.join(self.pasta.name, "teste.db")
        self.log = LogRequisicoes()
        self.app = criar_api(self.log, self.caminho_banco)

        @self.app.get("/api/v1/teste")
        def rota_teste():
            return {"ok": True}

        @self.app.get("/api/v1/falha")
        def rota_falha():
            raise RuntimeError("detalhe interno que não pode vazar")

        self.cliente = self.app.test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def assertCors(self, resposta):
        for nome, valor in CABECALHOS_CORS.items():
            self.assertEqual(resposta.headers.get(nome), valor, nome)

    def assertErroJson(self, resposta, status):
        self.assertEqual(resposta.status_code, status)
        self.assertTrue(resposta.is_json)
        self.assertIsInstance(resposta.get_json().get("mensagem"), str)
        self.assertCors(resposta)


class TestProtocoloBase(BaseComBanco):
    def test_options_responde_204_sem_corpo_com_cors(self):
        for caminho in ("/api/v1/users", "/api/v1/users/1", "/api/v1/sessions/abc", "/api/v1/teste"):
            r = self.cliente.options(caminho, headers={"Origin": "http://outro", "Access-Control-Request-Method": "DELETE"})
            self.assertEqual(r.status_code, 204, caminho)
            self.assertEqual(r.data, b"")
            self.assertCors(r)

    def test_options_nao_exige_token(self):
        r = self.cliente.options("/api/v1/users/1")
        self.assertEqual(r.status_code, 204)

    def test_rota_inexistente_404_json(self):
        self.assertErroJson(self.cliente.get("/api/v1/nao-existe"), 404)

    def test_barra_final_e_barra_dupla_nao_redirecionam(self):
        self.assertErroJson(self.cliente.get("/api/v1/teste/"), 404)
        self.assertErroJson(self.cliente.get("/api/v1//teste"), 404)

    def test_metodo_nao_suportado_405_json(self):
        r = self.cliente.post("/api/v1/teste")
        self.assertErroJson(r, 405)
        self.assertIn("GET", r.headers.get("Allow", ""))

    def test_erro_inesperado_500_json_sem_vazar_detalhes(self):
        r = self.cliente.get("/api/v1/falha")
        self.assertErroJson(r, 500)
        self.assertNotIn("detalhe interno", r.get_data(as_text=True))

    def test_resposta_de_sucesso_tambem_tem_cors(self):
        r = self.cliente.get("/api/v1/teste")
        self.assertEqual(r.status_code, 200)
        self.assertCors(r)

    def test_requisicoes_sao_registradas_no_log(self):
        self.cliente.get("/api/v1/teste")
        self.cliente.get("/api/v1/nao-existe")
        registros = self.log.listar()
        self.assertEqual([(r["metodo"], r["caminho"], r["status"]) for r in registros],
                         [("GET", "/api/v1/teste", 200), ("GET", "/api/v1/nao-existe", 404)])
        self.assertEqual(len(self.log.listar(desde_id=registros[0]["id"])), 1)


class TestBanco(BaseComBanco):
    @contextmanager
    def conexao(self):
        # O "with" do sqlite3 não fecha a conexão, e o Windows não apaga arquivo aberto.
        c = sqlite3.connect(self.caminho_banco)
        try:
            c.execute("PRAGMA foreign_keys = ON")
            with c:
                yield c
        finally:
            c.close()

    def test_tabelas_criadas(self):
        with self.conexao() as c:
            tabelas = {l[0] for l in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"users", "sessions"} <= tabelas)

    def test_email_unico_sem_diferenciar_maiusculas(self):
        with self.conexao() as c:
            c.execute("INSERT INTO users (nome, email, senha_hash) VALUES ('Ana', 'ana@x.com', 'h')")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("INSERT INTO users (nome, email, senha_hash) VALUES ('Ana', 'ANA@X.COM', 'h')")

    def test_id_de_usuario_excluido_nao_e_reaproveitado(self):
        with self.conexao() as c:
            c.execute("INSERT INTO users (nome, email, senha_hash) VALUES ('Ana', 'a@x.com', 'h')")
            c.execute("DELETE FROM users")
            c.execute("INSERT INTO users (nome, email, senha_hash) VALUES ('Bia', 'b@x.com', 'h')")
            self.assertEqual(c.execute("SELECT id FROM users").fetchone()[0], 2)

    def test_excluir_usuario_remove_sessoes(self):
        with self.conexao() as c:
            c.execute("INSERT INTO users (nome, email, senha_hash) VALUES ('Ana', 'a@x.com', 'h')")
            c.execute("INSERT INTO sessions VALUES ('s1', 't1', 1, '2026-01-01')")
            c.execute("DELETE FROM users WHERE id = 1")
            self.assertEqual(c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)

    def test_inicializar_duas_vezes_nao_apaga_dados(self):
        with self.conexao() as c:
            c.execute("INSERT INTO users (nome, email, senha_hash) VALUES ('Ana', 'a@x.com', 'h')")
        criar_api(LogRequisicoes(), self.caminho_banco)
        with self.conexao() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)


class TestPorta(unittest.TestCase):
    def test_portas_invalidas(self):
        for valor in ("", "abc", "80", "70000", "-1", "8080.5", "5000", "5001"):
            with self.assertRaises(ValueError, msg=valor):
                validar_porta(valor)

    def test_porta_valida(self):
        porta = porta_livre()
        self.assertEqual(validar_porta(f" {porta} "), porta)

    def test_porta_em_uso(self):
        with socket.socket() as ocupado:
            ocupado.bind(("0.0.0.0", 0))
            ocupado.listen()
            with self.assertRaises(ValueError):
                validar_porta(ocupado.getsockname()[1])


class TestControleEPainelComRedeReal(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.log = LogRequisicoes()
        caminho = os.path.join(self.pasta.name, "teste.db")
        self.controle = ControleAPI(lambda: criar_api(self.log, caminho))
        self.painel = criar_painel(self.controle, self.log).test_client()

    def tearDown(self):
        if self.controle.estado()["rodando"]:
            self.controle.parar()
        self.pasta.cleanup()

    def test_iniciar_responder_pela_rede_e_parar(self):
        porta = porta_livre()
        r = self.painel.post("/iniciar", json={"porta": str(porta)})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.painel.get("/estado").get_json(), {"rodando": True, "porta": porta})

        resposta = requests.options(f"http://127.0.0.1:{porta}/api/v1/users", timeout=5)
        self.assertEqual(resposta.status_code, 204)
        self.assertEqual(resposta.headers["Access-Control-Allow-Origin"], "*")
        resposta = requests.get(f"http://127.0.0.1:{porta}/api/v1/xyz", timeout=5)
        self.assertEqual(resposta.status_code, 404)
        self.assertIn("mensagem", resposta.json())
        self.assertEqual(len(self.painel.get("/log?desde=0").get_json()["registros"]), 2)

        self.assertEqual(self.painel.post("/iniciar", json={"porta": str(porta)}).status_code, 400)
        self.assertEqual(self.painel.post("/parar", json={}).status_code, 200)
        with self.assertRaises(requests.ConnectionError):
            requests.get(f"http://127.0.0.1:{porta}/api/v1/xyz", timeout=2)

        self.assertEqual(self.painel.post("/iniciar", json={"porta": str(porta)}).status_code, 200)

    def test_painel_mensagens_de_erro(self):
        r = self.painel.post("/iniciar", json={"porta": "abc"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("números", r.get_json()["mensagem"])
        self.assertEqual(self.painel.post("/parar", json={}).status_code, 400)

    def test_painel_recusa_post_sem_json(self):
        r = self.painel.post("/iniciar", data="porta=8080", content_type="application/x-www-form-urlencoded")
        self.assertEqual(r.status_code, 415)

    def test_log_identifica_a_execucao(self):
        dados = self.painel.get("/log?desde=0").get_json()
        self.assertEqual(dados, {"execucao": self.log.execucao, "registros": []})
        self.assertNotEqual(LogRequisicoes().execucao, self.log.execucao)

    def test_pagina_do_painel(self):
        r = self.painel.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Porta da API", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
