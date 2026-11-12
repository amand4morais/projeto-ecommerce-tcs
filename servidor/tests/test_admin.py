import os
import sqlite3
import tempfile
import unittest
import uuid
from contextlib import closing

from api import CABECALHOS_CORS, criar_api
from banco import ADM_PADRAO, BancoDesatualizado
from log_requisicoes import LogRequisicoes

MARIA = {"nome": "Maria Silva", "email": "maria@exemplo.com", "senha": "Senha123"}
JOAO = {"nome": "Joao Souza", "email": "joao@exemplo.com", "senha": "Outra456"}


class BaseAdmin(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho_banco = os.path.join(self.pasta.name, "teste.db")
        self.cliente = criar_api(LogRequisicoes(), self.caminho_banco).test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def login(self, email, senha):
        return self.cliente.post("/api/v1/sessions", json={"email": email, "senha": senha})

    def login_adm(self):
        return self.login(ADM_PADRAO["email"], ADM_PADRAO["senha"]).get_json()

    def cadastrar(self, dados):
        return self.cliente.post("/api/v1/users", json=dados).get_json()["id"]

    def auth(self, sessao):
        return {"Authorization": f"Bearer {sessao['token']}"}

    def consultar(self, sql, parametros=()):
        with closing(sqlite3.connect(self.caminho_banco)) as c:
            return c.execute(sql, parametros).fetchall()

    def assertErro(self, resposta, status):
        self.assertEqual(resposta.status_code, status, resposta.get_data(as_text=True))
        self.assertEqual(list(resposta.get_json()), ["mensagem"])
        for nome, valor in CABECALHOS_CORS.items():
            self.assertEqual(resposta.headers.get(nome), valor)


class TestAdmPadrao(BaseAdmin):
    def test_criado_na_inicializacao(self):
        [(nome, email, admin)] = self.consultar("SELECT nome, email, admin FROM users")
        self.assertEqual((nome, email, admin), ("Admin", "adm@teste.com", 1))

    def test_login_do_adm_devolve_admin_true(self):
        r = self.login("ADM@teste.com", "admin123")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["usuario"], {"id": 1, "nome": "Admin", "email": "adm@teste.com", "admin": True})

    def test_nao_duplica_ao_reiniciar(self):
        criar_api(LogRequisicoes(), self.caminho_banco)
        criar_api(LogRequisicoes(), self.caminho_banco)
        self.assertEqual(len(self.consultar("SELECT id FROM users")), 1)

    def test_nao_altera_adm_existente(self):
        adm = self.login_adm()
        self.cliente.patch("/api/v1/users/1", json={"nome": "Chefe"}, headers=self.auth(adm))
        criar_api(LogRequisicoes(), self.caminho_banco)
        self.assertEqual(self.consultar("SELECT nome FROM users"), [("Chefe",)])

    def test_recriado_se_removido(self):
        adm = self.login_adm()
        self.assertEqual(self.cliente.delete("/api/v1/users/1", headers=self.auth(adm)).status_code, 204)
        self.assertEqual(self.consultar("SELECT id FROM users"), [])
        criar_api(LogRequisicoes(), self.caminho_banco)
        self.assertEqual(self.consultar("SELECT id, email, admin FROM users"), [(2, "adm@teste.com", 1)])

    def test_recriado_se_trocar_o_email(self):
        adm = self.login_adm()
        self.cliente.patch("/api/v1/users/1", json={"email": "outro@teste.com"}, headers=self.auth(adm))
        criar_api(LogRequisicoes(), self.caminho_banco)
        self.assertEqual(len(self.consultar("SELECT id FROM users WHERE admin = 1")), 2)

    def test_banco_de_versao_anterior_e_recusado(self):
        antigo = os.path.join(self.pasta.name, "antigo.db")
        with closing(sqlite3.connect(antigo)) as c:
            c.executescript(
                "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL,"
                " email TEXT NOT NULL UNIQUE COLLATE NOCASE, senha_hash TEXT NOT NULL);"
                "CREATE TABLE sessions (id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,"
                " usuario_id INTEGER NOT NULL, criado_em TEXT NOT NULL);"
            )
        with self.assertRaises(BancoDesatualizado) as contexto:
            criar_api(LogRequisicoes(), antigo)
        self.assertIn("Apague servidor/ecommerce.db", str(contexto.exception))


class TestAdmGerenciaUsuarios(BaseAdmin):
    def setUp(self):
        super().setUp()
        self.id_maria = self.cadastrar(MARIA)
        self.id_joao = self.cadastrar(JOAO)
        self.adm = self.login_adm()
        self.maria = self.login(MARIA["email"], MARIA["senha"]).get_json()
        self.url_maria = f"/api/v1/users/{self.id_maria}"

    def test_listar_usuarios(self):
        r = self.cliente.get("/api/v1/users", headers=self.auth(self.adm))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
        self.assertEqual(r.get_json(), [
            {"id": 1, "nome": "Admin", "email": "adm@teste.com", "admin": True},
            {"id": self.id_maria, "nome": "Maria Silva", "email": "maria@exemplo.com", "admin": False},
            {"id": self.id_joao, "nome": "Joao Souza", "email": "joao@exemplo.com", "admin": False},
        ])

    def test_listar_exige_adm_e_token(self):
        self.assertErro(self.cliente.get("/api/v1/users", headers=self.auth(self.maria)), 403)
        self.assertErro(self.cliente.get("/api/v1/users"), 401)
        self.assertErro(self.cliente.get("/api/v1/users", headers={"Authorization": "Bearer x"}), 401)

    def test_adm_le_outro_usuario(self):
        r = self.cliente.get(self.url_maria, headers=self.auth(self.adm))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"id": self.id_maria, "nome": "Maria Silva", "email": "maria@exemplo.com", "admin": False})

    def test_adm_atualiza_outro_com_put_e_patch(self):
        novo = {"nome": "Maria Souza", "email": "maria.souza@exemplo.com", "senha": "Nova789"}
        r = self.cliente.put(self.url_maria, json=novo, headers=self.auth(self.adm))
        self.assertEqual(r.get_json(), {"id": self.id_maria, "nome": "Maria Souza", "email": "maria.souza@exemplo.com", "admin": False})
        r = self.cliente.patch(self.url_maria, json={"nome": "Maria Clara"}, headers=self.auth(self.adm))
        self.assertEqual((r.status_code, r.get_json()["nome"]), (200, "Maria Clara"))
        self.assertEqual(self.login("maria.souza@exemplo.com", "Nova789").status_code, 201)

    def test_adm_recebe_409_com_email_de_outro(self):
        r = self.cliente.patch(self.url_maria, json={"email": "JOAO@exemplo.com"}, headers=self.auth(self.adm))
        self.assertErro(r, 409)

    def test_admin_no_corpo_e_ignorado(self):
        for metodo, corpo in (("patch", {"admin": True, "nome": "Maria ADM"}), ("put", {**MARIA, "admin": True})):
            r = getattr(self.cliente, metodo)(self.url_maria, json=corpo, headers=self.auth(self.adm))
            self.assertFalse(r.get_json()["admin"])
        self.assertErro(self.cliente.patch(self.url_maria, json={"admin": True}, headers=self.auth(self.adm)), 400)
        self.assertEqual(self.consultar("SELECT admin FROM users WHERE id = ?", (self.id_maria,)), [(0,)])

    def test_adm_apaga_outro_e_derruba_as_sessoes_dele(self):
        r = self.cliente.delete(self.url_maria, headers=self.auth(self.adm))
        self.assertEqual(r.status_code, 204)
        self.assertErro(self.cliente.get(self.url_maria, headers=self.auth(self.maria)), 401)
        self.assertErro(self.cliente.get(self.url_maria, headers=self.auth(self.adm)), 404)
        self.assertEqual(self.cliente.get("/api/v1/users/1", headers=self.auth(self.adm)).status_code, 200)

    def test_adm_com_id_inexistente_recebe_404(self):
        for metodo in ("get", "put", "patch", "delete"):
            r = getattr(self.cliente, metodo)("/api/v1/users/999", json=MARIA, headers=self.auth(self.adm))
            self.assertErro(r, 404)

    def test_adm_ordem_404_antes_do_corpo_e_400_do_id(self):
        self.assertErro(self.cliente.patch("/api/v1/users/999", json={}, headers=self.auth(self.adm)), 404)
        self.assertErro(self.cliente.patch("/api/v1/users/abc", json={}, headers=self.auth(self.adm)), 400)
        self.assertErro(self.cliente.patch(self.url_maria, json={}, headers=self.auth(self.adm)), 400)

    def test_comum_continua_restrito(self):
        for id_ in (1, self.id_joao, 999):
            for metodo in ("get", "put", "patch", "delete"):
                r = getattr(self.cliente, metodo)(f"/api/v1/users/{id_}", json=MARIA, headers=self.auth(self.maria))
                self.assertErro(r, 403)

    def test_adm_nao_encerra_sessao_alheia_nem_inexistente(self):
        self.assertErro(self.cliente.delete(f"/api/v1/sessions/{self.maria['id']}", headers=self.auth(self.adm)), 403)
        self.assertErro(self.cliente.delete(f"/api/v1/sessions/{uuid.uuid4()}", headers=self.auth(self.adm)), 403)
        self.assertEqual(self.cliente.get(self.url_maria, headers=self.auth(self.maria)).status_code, 200)

    def test_sessao_guarda_o_ip(self):
        self.assertEqual(self.consultar("SELECT ip FROM sessions WHERE id = ?", (self.adm["id"],)), [("127.0.0.1",)])


if __name__ == "__main__":
    unittest.main()
