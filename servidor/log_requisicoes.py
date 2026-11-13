import json
import secrets
import threading
import time
from collections import deque
from datetime import datetime

LIMITE_REGISTROS = 200
LIMITE_TEXTO = 2000
JANELA_CLIENTES_ATIVOS = 300


def mascarar_token(token):
    return f"{token[:4]}…{token[-4:]}" if len(token) > 10 else "***"


def mascarar_autorizacao(valor):
    if not valor:
        return None
    esquema, espaco, token = valor.partition(" ")
    if espaco and token:
        return f"{esquema} {mascarar_token(token)}"
    return mascarar_token(valor)


def preparar_corpo(texto):
    if not texto:
        return None
    try:
        dados = json.loads(texto)
    except ValueError:
        return texto[:LIMITE_TEXTO]
    if isinstance(dados, dict) and isinstance(dados.get("token"), str):
        dados = {**dados, "token": mascarar_token(dados["token"])}
    return json.dumps(dados, ensure_ascii=False, indent=2)[:LIMITE_TEXTO]


class LogRequisicoes:
    def __init__(self, limite=LIMITE_REGISTROS):
        self.execucao = secrets.token_hex(8)
        self._registros = deque(maxlen=limite)
        self._proximo_id = 1
        self._trava = threading.Lock()

    def registrar(self, ip, metodo, caminho, status, autorizacao=None, corpo_recebido=None, corpo_resposta=None):
        with self._trava:
            self._registros.append({
                "id": self._proximo_id,
                "hora": datetime.now().strftime("%H:%M:%S"),
                "momento": time.time(),
                "ip": ip,
                "metodo": metodo,
                "caminho": caminho,
                "status": status,
                "autorizacao": mascarar_autorizacao(autorizacao),
                "corpo_recebido": preparar_corpo(corpo_recebido),
                "corpo_resposta": preparar_corpo(corpo_resposta),
            })
            self._proximo_id += 1

    def listar(self, desde_id=0):
        with self._trava:
            return [r for r in self._registros if r["id"] > desde_id]

    def total(self):
        with self._trava:
            return self._proximo_id - 1

    def clientes_ativos(self, janela=JANELA_CLIENTES_ATIVOS):
        limite = time.time() - janela
        with self._trava:
            return len({r["ip"] for r in self._registros if r["momento"] >= limite})
