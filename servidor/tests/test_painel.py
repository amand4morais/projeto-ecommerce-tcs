import json
import os
import tempfile
import time
import unittest
from unittest import mock

from api import criar_api
from banco import ADM_PADRAO
from controle_api import ControleAPI
from log_requisicoes import LIMITE_TEXTO, LogRequisicoes
from painel import criar_painel

MARIA = {"nome": "Maria Silva", "email": "maria@exemplo.com", "senha": "Senha123"}


class TestLogDetalhado(unittest.TestCase):
    def setUp(self):
        self.log = LogRequisicoes()

    def test_registra_corpos_e_mascara_o_token(self):
        token = "abcdefghijklmnopqrstuvwxyz"
        resposta = json.dumps({"id": "s1", "token": token, "usuario": {"id": 1}})
        self.log.registrar("10.0.0.5", "POST", "/api/v1/sessions", 201,
                           autorizacao=f"Bearer {token}", corpo_recebido='{"email":"a@b.com","senha":"abc123"}',
                           corpo_resposta=resposta)
        [r] = self.log.listar()
        self.assertEqual(r["autorizacao"], "Bearer abcd…wxyz")
        self.assertIn('"senha": "abc123"', r["corpo_recebido"])
        self.assertIn('"token": "abcd…wxyz"', r["corpo_resposta"])
        self.assertNotIn(token, json.dumps(r))

    def test_corpos_vazios_texto_e_limite(self):
        self.log.registrar("ip", "GET", "/x", 200, corpo_recebido="", corpo_resposta=None)
        self.log.registrar("ip", "POST", "/x", 400, corpo_recebido="nome=Ana", corpo_resposta="<h1>x</h1>")
        self.log.registrar("ip", "POST", "/x", 400, corpo_recebido="x" * 5000)
        vazio, texto, longo = self.log.listar()
        self.assertEqual((vazio["corpo_recebido"], vazio["corpo_resposta"], vazio["autorizacao"]), (None, None, None))
        self.assertEqual((texto["corpo_recebido"], texto["corpo_resposta"]), ("nome=Ana", "<h1>x</h1>"))
        self.assertEqual(len(longo["corpo_recebido"]), LIMITE_TEXTO)

    def test_autorizacao_sem_esquema_tambem_e_mascarada(self):
        self.log.registrar("ip", "GET", "/x", 401, autorizacao="tokensemesquema123")
        self.assertEqual(self.log.listar()[0]["autorizacao"], "toke…a123")

    def test_total_e_clientes_ativos(self):
        for ip in ("10.0.0.1", "10.0.0.2", "10.0.0.1"):
            self.log.registrar(ip, "GET", "/x", 200)
        self.assertEqual(self.log.total(), 3)
        self.assertEqual(self.log.clientes_ativos(), 2)
        with mock.patch("log_requisicoes.time.time", return_value=time.time() + 301):
            self.assertEqual(self.log.clientes_ativos(), 0)


class TestPainel(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho_banco = os.path.join(self.pasta.name, "teste.db")
        self.log = LogRequisicoes()
        self.api = criar_api(self.log, self.caminho_banco).test_client()
        controle = ControleAPI(lambda: criar_api(self.log, self.caminho_banco))
        self.painel = criar_painel(controle, self.log, self.caminho_banco).test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def login(self, email, senha):
        return self.api.post("/api/v1/sessions", json={"email": email, "senha": senha}).get_json()

    def logados(self):
        r = self.painel.get("/usuarios-logados")
        self.assertEqual(r.status_code, 200)
        return r.get_json()

    def test_paginas(self):
        self.assertIn("Porta da API", self.painel.get("/").get_data(as_text=True))
        self.assertIn("lista-detalhada", self.painel.get("/comunicacao").get_data(as_text=True))

    def test_lista_de_usuarios_logados_acompanha_login_logout_e_exclusao(self):
        self.assertEqual(self.logados(), [])
        self.api.post("/api/v1/users", json=MARIA)
        adm = self.login(ADM_PADRAO["email"], ADM_PADRAO["senha"])
        maria1 = self.login(MARIA["email"], MARIA["senha"])
        maria2 = self.login(MARIA["email"], MARIA["senha"])

        logados = {u["email"]: u for u in self.logados()}
        self.assertEqual(set(logados), {"adm@teste.com", "maria@exemplo.com"})
        self.assertEqual(logados["maria@exemplo.com"]["sessoes"], 2)
        self.assertEqual(logados["maria@exemplo.com"]["ip"], "127.0.0.1")
        self.assertTrue(logados["adm@teste.com"]["admin"])
        self.assertFalse(logados["maria@exemplo.com"]["admin"])
        self.assertTrue(logados["maria@exemplo.com"]["ultimo_login"])

        self.api.delete(f"/api/v1/sessions/{maria1['id']}", headers={"Authorization": f"Bearer {maria1['token']}"})
        self.assertEqual({u["email"]: u["sessoes"] for u in self.logados()}["maria@exemplo.com"], 1)

        id_maria = maria2["usuario"]["id"]
        self.api.delete(f"/api/v1/users/{id_maria}", headers={"Authorization": f"Bearer {adm['token']}"})
        self.assertEqual([u["email"] for u in self.logados()], ["adm@teste.com"])

    def test_sem_banco_nao_cria_arquivo(self):
        outro = os.path.join(self.pasta.name, "inexistente.db")
        painel = criar_painel(None, self.log, outro).test_client()
        self.assertEqual(painel.get("/usuarios-logados").get_json(), [])
        self.assertFalse(os.path.exists(outro))

    def test_indicadores(self):
        self.api.get("/api/v1/products")
        dados = self.painel.get("/indicadores").get_json()
        self.assertEqual((dados["requisicoes"], dados["clientes_ativos"]), (1, 1))
        self.assertIsInstance(dados["enderecos"], list)
        self.assertFalse(any(ip.startswith("127.") for ip in dados["enderecos"]))

    def test_api_registra_o_que_recebeu_e_respondeu(self):
        self.api.post("/api/v1/users", json=MARIA)
        sessao = self.login(MARIA["email"], MARIA["senha"])
        self.api.get("/api/v1/products", headers={"Authorization": f"Bearer {sessao['token']}"})
        cadastro, login, listagem = self.painel.get("/log?desde=0").get_json()["registros"]
        self.assertIn('"nome": "Maria Silva"', cadastro["corpo_recebido"])
        self.assertIn('"admin": false', cadastro["corpo_resposta"])
        self.assertNotIn(sessao["token"], login["corpo_resposta"])
        self.assertTrue(listagem["autorizacao"].startswith("Bearer "))
        self.assertNotIn(sessao["token"], listagem["autorizacao"])
        self.assertEqual((listagem["corpo_recebido"], listagem["corpo_resposta"]), (None, "[]"))


if __name__ == "__main__":
    unittest.main()
