import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

from api import CABECALHOS_CORS, criar_api
from log_requisicoes import LogRequisicoes

URL = "/api/v1/users"
VALIDO = {"nome": "Maria Silva", "email": "maria@exemplo.com", "senha": "Senha123"}


class TestCadastroUsuario(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho_banco = os.path.join(self.pasta.name, "teste.db")
        self.cliente = criar_api(LogRequisicoes(), self.caminho_banco).test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def cadastrar(self, **alteracoes):
        return self.cliente.post(URL, json={**VALIDO, **alteracoes})

    def usuarios_no_banco(self):
        with closing(sqlite3.connect(self.caminho_banco)) as c:
            return c.execute("SELECT id, nome, email, senha_hash FROM users").fetchall()

    def assertErro(self, resposta, status):
        self.assertEqual(resposta.status_code, status, resposta.get_data(as_text=True))
        self.assertEqual(list(resposta.get_json()), ["mensagem"])
        self.assertEqual(resposta.headers["Access-Control-Allow-Origin"], CABECALHOS_CORS["Access-Control-Allow-Origin"])

    def test_cadastro_valido(self):
        r = self.cadastrar()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json(), {"id": 1, "nome": "Maria Silva", "email": "maria@exemplo.com"})
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
        [(id_, nome, email, senha_hash)] = self.usuarios_no_banco()
        self.assertEqual((id_, nome, email), (1, "Maria Silva", "maria@exemplo.com"))
        self.assertNotIn("Senha123", senha_hash)

    def test_ids_sequenciais(self):
        self.cadastrar()
        r = self.cadastrar(email="joao@exemplo.com")
        self.assertEqual(r.get_json()["id"], 2)

    def test_nome_com_trim(self):
        r = self.cadastrar(nome="   Ana   ")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["nome"], "Ana")
        self.assertErro(self.cadastrar(nome="  Al  ", email="x@y.com"), 400)

    def test_limites_do_nome(self):
        self.assertErro(self.cadastrar(nome="ab"), 400)
        self.assertErro(self.cadastrar(nome="a" * 51), 400)
        self.assertEqual(self.cadastrar(nome="abc", email="a1@b.com").status_code, 201)
        self.assertEqual(self.cadastrar(nome="a" * 50, email="a2@b.com").status_code, 201)

    def test_limites_do_email(self):
        self.assertErro(self.cadastrar(email="a@b."), 400)
        self.assertErro(self.cadastrar(email="a" * 25 + "@b.com"), 400)
        self.assertEqual(self.cadastrar(email="a@b.c").status_code, 201)
        self.assertEqual(self.cadastrar(email="a" * 24 + "@b.com").status_code, 201)

    def test_formato_do_email(self):
        for email in ("semarroba.com", "a@semponto", "a b@c.com", "a@@b.com", "@b.com", "a@b.com\n", " a@b.com"):
            self.assertErro(self.cadastrar(email=email), 400)

    def test_limites_da_senha(self):
        self.assertErro(self.cadastrar(senha="abc12"), 400)
        self.assertErro(self.cadastrar(senha="a" * 21), 400)
        self.assertEqual(self.cadastrar(senha="abc123", email="s1@b.com").status_code, 201)
        self.assertEqual(self.cadastrar(senha="a" * 20, email="s2@b.com").status_code, 201)

    def test_senha_somente_letras_e_numeros(self):
        for senha in ("Senha@123", "senha 123", "senhaç123", "senha_123"):
            self.assertErro(self.cadastrar(senha=senha), 400)

    def test_tipos_errados_e_null(self):
        for campo in ("nome", "email", "senha"):
            for valor in (123, True, None, ["x"], {"a": 1}):
                self.assertErro(self.cadastrar(**{campo: valor}), 400)
        self.assertEqual(self.usuarios_no_banco(), [])

    def test_campo_faltando(self):
        for campo in ("nome", "email", "senha"):
            dados = {k: v for k, v in VALIDO.items() if k != campo}
            r = self.cliente.post(URL, json=dados)
            self.assertErro(r, 400)
            self.assertIn(campo, r.get_json()["mensagem"])

    def test_primeiro_erro_na_ordem_nome_email_senha(self):
        r = self.cliente.post(URL, json={"nome": "a", "email": "x", "senha": "!"})
        self.assertIn("nome", r.get_json()["mensagem"])

    def test_corpo_invalido(self):
        self.assertErro(self.cliente.post(URL), 400)
        self.assertErro(self.cliente.post(URL, data="{nao e json", content_type="application/json"), 400)
        self.assertErro(self.cliente.post(URL, json=[VALIDO]), 400)
        self.assertErro(self.cliente.post(URL, json="texto"), 400)
        self.assertErro(self.cliente.post(URL, data="nome=Maria", content_type="application/x-www-form-urlencoded"), 400)

    def test_content_type_com_charset(self):
        r = self.cliente.post(URL, data='{"nome":"José","email":"jose@x.com","senha":"abc123"}'.encode("utf-8"),
                              content_type="application/json; charset=utf-8")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["nome"], "José")

    def test_email_duplicado_sem_diferenciar_maiusculas(self):
        self.cadastrar()
        r = self.cadastrar(email="MARIA@Exemplo.com", nome="Outra Maria")
        self.assertErro(r, 409)
        self.assertEqual(len(self.usuarios_no_banco()), 1)

    def test_campos_extras_e_id_no_corpo_ignorados(self):
        r = self.cadastrar(id=99, admin=True, idade=30)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json(), {"id": 1, "nome": "Maria Silva", "email": "maria@exemplo.com"})

    def test_outros_metodos_em_users_retornam_405(self):
        self.assertErro(self.cliente.get(URL), 405)
        self.assertErro(self.cliente.delete(URL), 405)


if __name__ == "__main__":
    unittest.main()
