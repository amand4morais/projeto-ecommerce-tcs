import os
import tempfile
import unittest

from api import CABECALHOS_CORS, criar_api
from banco import ADM_PADRAO
from log_requisicoes import LogRequisicoes

URL = "/api/v1/products"
TECLADO = {"nome": "Teclado mecânico", "descricao": "ABNT2, switch azul", "quantidade": 15}
MARIA = {"nome": "Maria Silva", "email": "maria@exemplo.com", "senha": "Senha123"}


class TestProdutos(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.cliente = criar_api(LogRequisicoes(), os.path.join(self.pasta.name, "teste.db")).test_client()
        self.cliente.post("/api/v1/users", json=MARIA)
        self.adm = self.auth(ADM_PADRAO["email"], ADM_PADRAO["senha"])
        self.comum = self.auth(MARIA["email"], MARIA["senha"])

    def tearDown(self):
        self.pasta.cleanup()

    def auth(self, email, senha):
        sessao = self.cliente.post("/api/v1/sessions", json={"email": email, "senha": senha}).get_json()
        return {"Authorization": f"Bearer {sessao['token']}"}

    def cadastrar(self, **alteracoes):
        return self.cliente.post(URL, json={**TECLADO, **alteracoes}, headers=self.adm)

    def assertErro(self, resposta, status):
        self.assertEqual(resposta.status_code, status, resposta.get_data(as_text=True))
        self.assertEqual(list(resposta.get_json()), ["mensagem"])
        for nome, valor in CABECALHOS_CORS.items():
            self.assertEqual(resposta.headers.get(nome), valor)

    def assertProduto(self, resposta, status, esperado):
        self.assertEqual(resposta.status_code, status, resposta.get_data(as_text=True))
        self.assertEqual(resposta.get_json(), esperado)
        self.assertEqual(resposta.headers["Access-Control-Allow-Origin"], "*")

    def test_cadastro_pelo_adm(self):
        r = self.cadastrar()
        self.assertProduto(r, 201, {"id": 1, **TECLADO})
        self.assertEqual(r.headers["Location"], "/api/v1/products/1")

    def test_listagem_vazia_e_ordenada_para_qualquer_logado(self):
        self.assertProduto(self.cliente.get(URL, headers=self.comum), 200, [])
        self.cadastrar()
        self.cadastrar(nome="Mouse", descricao="", quantidade=0)
        esperado = [{"id": 1, **TECLADO}, {"id": 2, "nome": "Mouse", "descricao": "", "quantidade": 0}]
        self.assertProduto(self.cliente.get(URL, headers=self.comum), 200, esperado)
        self.assertProduto(self.cliente.get(URL, headers=self.adm), 200, esperado)

    def test_consulta_de_um_produto_por_qualquer_logado(self):
        self.cadastrar()
        self.assertProduto(self.cliente.get(f"{URL}/1", headers=self.comum), 200, {"id": 1, **TECLADO})
        self.assertProduto(self.cliente.get(f"{URL}/1", headers=self.adm), 200, {"id": 1, **TECLADO})

    def test_leituras_exigem_token(self):
        self.cadastrar()
        for url in (URL, f"{URL}/1", f"{URL}/abc", f"{URL}/999"):
            self.assertErro(self.cliente.get(url), 401)
            self.assertErro(self.cliente.get(url, headers={"Authorization": "Bearer inventado"}), 401)

    def test_consulta_id_invalido_e_inexistente(self):
        for id_ in ("abc", "-1", "1.5"):
            self.assertErro(self.cliente.get(f"{URL}/{id_}", headers=self.comum), 400)
        self.assertErro(self.cliente.get(f"{URL}/999", headers=self.comum), 404)

    def test_put_substitui_todos_os_campos(self):
        self.cadastrar()
        novo = {"nome": "Teclado sem fio", "descricao": "Bluetooth", "quantidade": 3}
        self.assertProduto(self.cliente.put(f"{URL}/1", json=novo, headers=self.adm), 200, {"id": 1, **novo})
        for campo in novo:
            parcial = {k: v for k, v in novo.items() if k != campo}
            self.assertErro(self.cliente.put(f"{URL}/1", json=parcial, headers=self.adm), 400)

    def test_patch_altera_so_o_enviado(self):
        self.cadastrar()
        r = self.cliente.patch(f"{URL}/1", json={"quantidade": 7}, headers=self.adm)
        self.assertProduto(r, 200, {"id": 1, **TECLADO, "quantidade": 7})
        r = self.cliente.patch(f"{URL}/1", json={"descricao": "  Nova  ", "id": 5, "extra": 1}, headers=self.adm)
        self.assertProduto(r, 200, {"id": 1, **TECLADO, "quantidade": 7, "descricao": "Nova"})

    def test_patch_sem_campos_reconhecidos(self):
        self.cadastrar()
        for corpo in ({}, {"preco": 10}, {"id": 2}):
            self.assertErro(self.cliente.patch(f"{URL}/1", json=corpo, headers=self.adm), 400)

    def test_remocao_pelo_adm(self):
        self.cadastrar()
        r = self.cliente.delete(f"{URL}/1", headers=self.adm)
        self.assertEqual((r.status_code, r.data), (204, b""))
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
        self.assertErro(self.cliente.get(f"{URL}/1", headers=self.adm), 404)
        self.assertProduto(self.cliente.get(URL, headers=self.adm), 200, [])
        self.assertEqual(self.cadastrar().get_json()["id"], 2)

    def test_comum_nao_escreve_exista_ou_nao(self):
        self.cadastrar()
        self.assertErro(self.cliente.post(URL, json=TECLADO, headers=self.comum), 403)
        for id_ in (1, 999):
            self.assertErro(self.cliente.put(f"{URL}/{id_}", json=TECLADO, headers=self.comum), 403)
            self.assertErro(self.cliente.patch(f"{URL}/{id_}", json={"quantidade": 1}, headers=self.comum), 403)
            self.assertErro(self.cliente.delete(f"{URL}/{id_}", headers=self.comum), 403)
        self.assertProduto(self.cliente.get(f"{URL}/1", headers=self.comum), 200, {"id": 1, **TECLADO})

    def test_adm_com_produto_inexistente_404(self):
        self.assertErro(self.cliente.put(f"{URL}/999", json=TECLADO, headers=self.adm), 404)
        self.assertErro(self.cliente.patch(f"{URL}/999", json={"quantidade": 1}, headers=self.adm), 404)
        self.assertErro(self.cliente.delete(f"{URL}/999", headers=self.adm), 404)

    def test_ordem_de_validacao(self):
        self.cadastrar()
        self.assertErro(self.cliente.patch(f"{URL}/abc", json={}), 401)
        self.assertErro(self.cliente.post(URL, json={}), 401)
        self.assertErro(self.cliente.patch(f"{URL}/abc", json={}, headers=self.comum), 400)
        self.assertErro(self.cliente.patch(f"{URL}/abc", json={}, headers=self.adm), 400)
        self.assertErro(self.cliente.patch(f"{URL}/999", json={}, headers=self.comum), 403)
        self.assertErro(self.cliente.post(URL, json={}, headers=self.comum), 403)
        self.assertErro(self.cliente.patch(f"{URL}/999", json={}, headers=self.adm), 404)
        self.assertErro(self.cliente.patch(f"{URL}/1", json={}, headers=self.adm), 400)

    def test_limites_do_nome(self):
        self.assertErro(self.cadastrar(nome="A"), 400)
        self.assertErro(self.cadastrar(nome="  A  "), 400)
        self.assertErro(self.cadastrar(nome="x" * 101), 400)
        self.assertEqual(self.cadastrar(nome="AB").status_code, 201)
        self.assertEqual(self.cadastrar(nome="x" * 100).status_code, 201)
        self.assertEqual(self.cadastrar(nome="  Mouse  ").get_json()["nome"], "Mouse")

    def test_nome_repetido_permitido(self):
        self.assertEqual(self.cadastrar().status_code, 201)
        self.assertEqual(self.cadastrar().get_json()["id"], 2)

    def test_limites_da_descricao(self):
        self.assertErro(self.cadastrar(descricao="x" * 501), 400)
        self.assertEqual(self.cadastrar(descricao="x" * 500).status_code, 201)
        self.assertEqual(self.cadastrar(descricao="").get_json()["descricao"], "")
        self.assertEqual(self.cadastrar(descricao="  y" + " " * 600).get_json()["descricao"], "y")

    def test_limites_da_quantidade(self):
        for valor in (-1, 1_000_001, 1.5, 10.0, "10", True, False, None, [1]):
            self.assertErro(self.cadastrar(quantidade=valor), 400)
            self.assertErro(self.cliente.patch(f"{URL}/1", json={"quantidade": valor}, headers=self.adm), 404)
        self.assertEqual(self.cadastrar(quantidade=0).status_code, 201)
        self.assertEqual(self.cadastrar(quantidade=1_000_000).status_code, 201)
        for valor in (-1, 1.5, "10", True, None):
            self.assertErro(self.cliente.patch(f"{URL}/1", json={"quantidade": valor}, headers=self.adm), 400)

    def test_tipos_errados_e_campos_faltando(self):
        for campo in ("nome", "descricao"):
            for valor in (123, True, None, ["x"]):
                self.assertErro(self.cadastrar(**{campo: valor}), 400)
        for campo in TECLADO:
            parcial = {k: v for k, v in TECLADO.items() if k != campo}
            self.assertErro(self.cliente.post(URL, json=parcial, headers=self.adm), 400)
        self.assertErro(self.cliente.post(URL, data="{x", content_type="application/json", headers=self.adm), 400)
        self.assertErro(self.cliente.post(URL, json=[TECLADO], headers=self.adm), 400)
        self.assertProduto(self.cliente.get(URL, headers=self.adm), 200, [])

    def test_options_e_metodos_nao_suportados(self):
        self.assertEqual(self.cliente.options(URL).status_code, 204)
        self.assertEqual(self.cliente.options(f"{URL}/1").status_code, 204)
        self.assertErro(self.cliente.delete(URL, headers=self.adm), 405)
        self.assertErro(self.cliente.post(f"{URL}/1", json=TECLADO, headers=self.adm), 405)


if __name__ == "__main__":
    unittest.main()
