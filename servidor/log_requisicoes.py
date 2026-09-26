import threading
from collections import deque
from datetime import datetime

LIMITE_REGISTROS = 200


class LogRequisicoes:
    def __init__(self, limite=LIMITE_REGISTROS):
        self._registros = deque(maxlen=limite)
        self._proximo_id = 1
        self._trava = threading.Lock()

    def registrar(self, ip, metodo, caminho, status):
        with self._trava:
            self._registros.append({
                "id": self._proximo_id,
                "hora": datetime.now().strftime("%H:%M:%S"),
                "ip": ip,
                "metodo": metodo,
                "caminho": caminho,
                "status": status,
            })
            self._proximo_id += 1

    def listar(self, desde_id=0):
        with self._trava:
            return [r for r in self._registros if r["id"] > desde_id]
