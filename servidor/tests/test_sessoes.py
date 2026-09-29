import hashlib
import os
import sqlite3
import tempfile
import unittest
import uuid
from contextlib import closing

from api import CABECALHOS_CORS, criar_api
from log_requisicoes import LogRequisicoes

MARIA = {"nome": "Maria Silva", "email": "maria@exemplo.com", "senha": "Senha123"}
JOAO = {"nome": "Joao Souza", "email": "joao@exemplo.com", "senha": "Outra456"}


class TestSessoes(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho_banco = os.path.join(self.pasta.name, "teste.db")
        self.cliente = criar_api(LogRequisicoes(), self.caminho_banco).test_client()
        self.id_maria = self.cliente.post("/api/v1/users", json=MARIA).get_json()["id"]
        self.cliente.post("/api/v1/users", json=JOAO)

    def tearDown(self):
        self.pasta.cleanup()

    def login(self, email, senha):
        return self.cliente.post("/api/v1/sessions", json={"email": email, "senha": senha})

    def logout(self, id_sessao, token):
        return self.cliente.delete(f"/api/v1/sessions/{id_sessao}", headers={"Authorization": f"Bearer {token}"})

    def sessoes_no_banco(self):
        with closing(sqlite3.connect(self.caminho_banco)) as c:
            return c.execute("SELECT id, token_hash, usuario_id FROM sessions").fetchall()

    def assertErro(self, resposta, status):
        self.assertEqual(resposta.status_code, status, resposta.get_data(as_text=True))
        self.assertEqual(list(resposta.get_json()), ["mensagem"])
        for nome, valor in CABECALHOS_CORS.items():
            self.assertEqual(resposta.headers.get(nome), valor)

    def test_login_valido(self):
        r = self.login("maria@exemplo.com", "Senha123")
        self.assertEqual(r.status_code, 201)
        dados = r.get_json()
        self.assertEqual(set(dados), {"id", "token", "usuario"})
        uuid.UUID(dados["id"])
        self.assertIsInstance(dados["token"], str)
        self.assertNotEqual(dados["id"], dados["token"])
        self.assertEqual(dados["usuario"], {"id": self.id_maria, "nome": "Maria Silva", "email": "maria@exemplo.com"})
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")

    def test_login_com_email_em_maiusculas(self):
        self.assertEqual(self.login("MARIA@Exemplo.COM", "Senha123").status_code, 201)

    def test_token_guardado_somente_como_hash(self):
        dados = self.login("maria@exemplo.com", "Senha123").get_json()
        [(id_sessao, token_hash, usuario_id)] = self.sessoes_no_banco()
        self.assertEqual((id_sessao, usuario_id), (dados["id"], self.id_maria))
        self.assertNotEqual(token_hash, dados["token"])
        self.assertEqual(token_hash, hashlib.sha256(dados["token"].encode()).hexdigest())

    def test_credenciais_invalidas_mesma_mensagem(self):
        senha_errada = self.login("maria@exemplo.com", "Errada123")
        email_inexistente = self.login("ninguem@exemplo.com", "Senha123")
        self.assertErro(senha_errada, 401)
        self.assertErro(email_inexistente, 401)
        self.assertEqual(senha_errada.get_json(), email_inexistente.get_json())
        self.assertEqual(self.sessoes_no_banco(), [])

    def test_login_corpo_invalido_400(self):
        url = "/api/v1/sessions"
        casos = [
            self.cliente.post(url),
            self.cliente.post(url, data="{x", content_type="application/json"),
            self.cliente.post(url, json=["maria@exemplo.com"]),
            self.cliente.post(url, json={"senha": "Senha123"}),
            self.cliente.post(url, json={"email": "maria@exemplo.com"}),
            self.cliente.post(url, json={"email": None, "senha": "Senha123"}),
            self.cliente.post(url, json={"email": "maria@exemplo.com", "senha": 123456}),
            self.login("semarroba", "Senha123"),
            self.login("a@b.c" + "x" * 30, "Senha123"),
            self.login("maria@exemplo.com", "abc"),
            self.login("maria@exemplo.com", "Senha@123"),
        ]
        for r in casos:
            self.assertErro(r, 400)

    def test_varios_logins_criam_sessoes_independentes(self):
        a = self.login("maria@exemplo.com", "Senha123").get_json()
        b = self.login("maria@exemplo.com", "Senha123").get_json()
        self.assertNotEqual(a["id"], b["id"])
        self.assertNotEqual(a["token"], b["token"])
        self.assertEqual(self.logout(a["id"], a["token"]).status_code, 204)
        self.assertEqual(len(self.sessoes_no_banco()), 1)
        self.assertEqual(self.logout(b["id"], b["token"]).status_code, 204)

    def test_logout_invalida_o_token(self):
        s = self.login("maria@exemplo.com", "Senha123").get_json()
        r = self.logout(s["id"], s["token"])
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.data, b"")
        self.assertNotIn("Content-Type", r.headers)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
        self.assertErro(self.logout(s["id"], s["token"]), 401)

    def test_logout_de_outra_sessao_propria(self):
        a = self.login("maria@exemplo.com", "Senha123").get_json()
        b = self.login("maria@exemplo.com", "Senha123").get_json()
        self.assertEqual(self.logout(a["id"], b["token"]).status_code, 204)
        self.assertErro(self.logout(b["id"], a["token"]), 401)

    def test_logout_de_sessao_de_outro_usuario_403(self):
        maria = self.login("maria@exemplo.com", "Senha123").get_json()
        joao = self.login("joao@exemplo.com", "Outra456").get_json()
        self.assertErro(self.logout(joao["id"], maria["token"]), 403)
        self.assertEqual(len(self.sessoes_no_banco()), 2)

    def test_logout_de_sessao_inexistente_404(self):
        s = self.login("maria@exemplo.com", "Senha123").get_json()
        self.assertErro(self.logout(str(uuid.uuid4()), s["token"]), 404)
        self.assertErro(self.logout("qualquer-texto", s["token"]), 404)

    def test_logout_sem_token_ou_token_invalido_401(self):
        s = self.login("maria@exemplo.com", "Senha123").get_json()
        url = f"/api/v1/sessions/{s['id']}"
        for cabecalhos in ({}, {"Authorization": s["token"]}, {"Authorization": "Bearer "},
                           {"Authorization": "Basic " + s["token"]}, {"Authorization": "Bearer inventado"}):
            self.assertErro(self.cliente.delete(url, headers=cabecalhos), 401)
        self.assertEqual(len(self.sessoes_no_banco()), 1)

    def test_401_vem_antes_de_404_e_403(self):
        self.assertErro(self.cliente.delete(f"/api/v1/sessions/{uuid.uuid4()}"), 401)

    def test_bearer_sem_diferenciar_maiusculas(self):
        s = self.login("maria@exemplo.com", "Senha123").get_json()
        r = self.cliente.delete(f"/api/v1/sessions/{s['id']}", headers={"Authorization": f"bearer {s['token']}"})
        self.assertEqual(r.status_code, 204)

    def test_metodos_nao_suportados(self):
        self.assertErro(self.cliente.get("/api/v1/sessions"), 405)
        self.assertErro(self.cliente.delete("/api/v1/sessions"), 405)


if __name__ == "__main__":
    unittest.main()
