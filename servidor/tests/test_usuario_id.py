import hashlib
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

from api import CABECALHOS_CORS, criar_api
from log_requisicoes import LogRequisicoes

MARIA = {"nome": "Maria Silva", "email": "maria@exemplo.com", "senha": "Senha123"}
JOAO = {"nome": "Joao Souza", "email": "joao@exemplo.com", "senha": "Outra456"}


class TestUsuarioPorId(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho_banco = os.path.join(self.pasta.name, "teste.db")
        self.cliente = criar_api(LogRequisicoes(), self.caminho_banco).test_client()
        self.id_maria = self.cliente.post("/api/v1/users", json=MARIA).get_json()["id"]
        self.id_joao = self.cliente.post("/api/v1/users", json=JOAO).get_json()["id"]
        self.sessao_maria = self.login(MARIA["email"], MARIA["senha"])
        self.token = self.sessao_maria["token"]
        self.url = f"/api/v1/users/{self.id_maria}"

    def tearDown(self):
        self.pasta.cleanup()

    def login(self, email, senha):
        return self.cliente.post("/api/v1/sessions", json={"email": email, "senha": senha}).get_json()

    def auth(self, token=None):
        return {"Authorization": f"Bearer {token or self.token}"}

    def assertErro(self, resposta, status):
        self.assertEqual(resposta.status_code, status, resposta.get_data(as_text=True))
        self.assertEqual(list(resposta.get_json()), ["mensagem"])
        for nome, valor in CABECALHOS_CORS.items():
            self.assertEqual(resposta.headers.get(nome), valor)

    def assertUsuario(self, resposta, esperado):
        self.assertEqual(resposta.status_code, 200, resposta.get_data(as_text=True))
        self.assertEqual(resposta.get_json(), esperado)
        self.assertEqual(resposta.headers["Access-Control-Allow-Origin"], "*")

    def test_get_proprio_usuario(self):
        r = self.cliente.get(self.url, headers=self.auth())
        self.assertUsuario(r, {"id": self.id_maria, "nome": "Maria Silva", "email": "maria@exemplo.com"})

    def test_put_substitui_todos_os_campos(self):
        novo = {"nome": "Maria Souza", "email": "maria.souza@exemplo.com", "senha": "Nova789"}
        r = self.cliente.put(self.url, json=novo, headers=self.auth())
        self.assertUsuario(r, {"id": self.id_maria, "nome": "Maria Souza", "email": "maria.souza@exemplo.com"})
        self.assertIsNotNone(self.login("maria.souza@exemplo.com", "Nova789").get("token"))
        self.assertIsNone(self.login("maria@exemplo.com", "Senha123").get("token"))

    def test_put_exige_todos_os_campos(self):
        for campo in ("nome", "email", "senha"):
            dados = {k: v for k, v in MARIA.items() if k != campo}
            self.assertErro(self.cliente.put(self.url, json=dados, headers=self.auth()), 400)

    def test_patch_altera_somente_campo_enviado(self):
        r = self.cliente.patch(self.url, json={"nome": "  Maria Clara  "}, headers=self.auth())
        self.assertUsuario(r, {"id": self.id_maria, "nome": "Maria Clara", "email": "maria@exemplo.com"})
        self.assertIsNotNone(self.login("maria@exemplo.com", "Senha123").get("token"))

    def test_patch_de_senha_mantem_sessao_e_troca_login(self):
        r = self.cliente.patch(self.url, json={"senha": "Trocada1"}, headers=self.auth())
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("senha", r.get_json())
        self.assertEqual(self.cliente.get(self.url, headers=self.auth()).status_code, 200)
        self.assertIsNotNone(self.login("maria@exemplo.com", "Trocada1").get("token"))

    def test_patch_sem_campos_reconhecidos(self):
        for corpo in ({}, {"idade": 30}, {"id": 5}):
            self.assertErro(self.cliente.patch(self.url, json=corpo, headers=self.auth()), 400)

    def test_patch_valida_campos_enviados(self):
        for corpo in ({"nome": "ab"}, {"email": "invalido"}, {"senha": "curta"}, {"nome": None}, {"email": 10}):
            self.assertErro(self.cliente.patch(self.url, json=corpo, headers=self.auth()), 400)

    def test_email_de_outro_usuario_409(self):
        self.assertErro(self.cliente.patch(self.url, json={"email": "JOAO@exemplo.com"}, headers=self.auth()), 409)
        dados = {**MARIA, "email": "joao@exemplo.com"}
        self.assertErro(self.cliente.put(self.url, json=dados, headers=self.auth()), 409)

    def test_proprio_email_com_outras_maiusculas_permitido(self):
        r = self.cliente.patch(self.url, json={"email": "MARIA@exemplo.com"}, headers=self.auth())
        self.assertUsuario(r, {"id": self.id_maria, "nome": "Maria Silva", "email": "MARIA@exemplo.com"})

    def test_campos_extras_e_id_no_corpo_ignorados(self):
        r = self.cliente.patch(self.url, json={"nome": "Maria Nova", "id": self.id_joao, "admin": True}, headers=self.auth())
        self.assertUsuario(r, {"id": self.id_maria, "nome": "Maria Nova", "email": "maria@exemplo.com"})

    def test_delete_remove_usuario_e_todas_as_sessoes(self):
        outra_sessao = self.login(MARIA["email"], MARIA["senha"])
        r = self.cliente.delete(self.url, headers=self.auth())
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.data, b"")
        self.assertNotIn("Content-Type", r.headers)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
        self.assertErro(self.cliente.get(self.url, headers=self.auth()), 401)
        self.assertErro(self.cliente.get(self.url, headers=self.auth(outra_sessao["token"])), 401)
        self.assertIsNone(self.login(MARIA["email"], MARIA["senha"]).get("token"))
        with closing(sqlite3.connect(self.caminho_banco)) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM sessions WHERE usuario_id = ?", (self.id_maria,)).fetchone()[0], 0)

    def test_delete_nao_afeta_outro_usuario(self):
        sessao_joao = self.login(JOAO["email"], JOAO["senha"])
        self.cliente.delete(self.url, headers=self.auth())
        r = self.cliente.get(f"/api/v1/users/{self.id_joao}", headers=self.auth(sessao_joao["token"]))
        self.assertEqual(r.status_code, 200)

    def test_sem_token_401_em_todas_as_rotas(self):
        for metodo in ("get", "put", "patch", "delete"):
            self.assertErro(getattr(self.cliente, metodo)(self.url, json=MARIA), 401)
            self.assertErro(getattr(self.cliente, metodo)(self.url, json=MARIA, headers=self.auth("inventado")), 401)

    def test_id_mal_formatado_400(self):
        for id_ in ("abc", "-1", "1.5", "1e3", "²", "%20"):
            for metodo in ("get", "put", "patch", "delete"):
                r = getattr(self.cliente, metodo)(f"/api/v1/users/{id_}", json=MARIA, headers=self.auth())
                self.assertErro(r, 400)

    def test_id_de_outro_usuario_existente_ou_nao_403(self):
        for id_ in (self.id_joao, 999, 0):
            for metodo in ("get", "put", "patch", "delete"):
                r = getattr(self.cliente, metodo)(f"/api/v1/users/{id_}", json=MARIA, headers=self.auth())
                self.assertErro(r, 403)
        self.assertEqual(self.cliente.get(f"/api/v1/users/{self.id_joao}", headers=self.auth(
            self.login(JOAO["email"], JOAO["senha"])["token"])).status_code, 200)

    def test_id_com_zero_a_esquerda(self):
        r = self.cliente.get(f"/api/v1/users/0{self.id_maria}", headers=self.auth())
        self.assertEqual(r.status_code, 200)

    def test_ordem_de_validacao(self):
        self.assertErro(self.cliente.get("/api/v1/users/abc"), 401)
        self.assertErro(self.cliente.patch("/api/v1/users/abc", json={}, headers=self.auth()), 400)
        self.assertErro(self.cliente.patch(f"/api/v1/users/{self.id_joao}", json={}, headers=self.auth()), 403)
        self.assertErro(self.cliente.patch(f"/api/v1/users/{self.id_joao}", json={"email": "joao@exemplo.com"},
                                           headers=self.auth()), 403)
        self.assertErro(self.cliente.put(self.url, data="{x", content_type="application/json", headers=self.auth()), 400)

    def test_usuario_inexistente_404(self):
        token = "token-de-usuario-inexistente"
        with closing(sqlite3.connect(self.caminho_banco)) as c:
            c.execute("INSERT INTO sessions VALUES ('s-orfa', ?, 999, '2026-01-01')",
                      (hashlib.sha256(token.encode()).hexdigest(),))
            c.commit()
        self.assertErro(self.cliente.get("/api/v1/users/999", headers=self.auth(token)), 404)

    def test_options_e_metodo_nao_suportado(self):
        self.assertEqual(self.cliente.options(self.url).status_code, 204)
        self.assertErro(self.cliente.post(self.url, json=MARIA, headers=self.auth()), 405)


if __name__ == "__main__":
    unittest.main()
