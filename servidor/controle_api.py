import socket
import sys
import threading

from werkzeug.serving import make_server

PORTA_PAINEL = 5000
PORTA_CLIENTE = 5001
PORTA_MINIMA = 1024
PORTA_MAXIMA = 65535


def porta_em_uso(porta):
    teste = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if sys.platform == "win32":
            # Sem esta opção, o Windows permite o bind numa porta já ocupada.
            teste.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        teste.bind(("0.0.0.0", porta))
        return False
    except OSError:
        return True
    finally:
        teste.close()


def validar_porta(valor):
    texto = str(valor).strip()
    if not texto.isdigit():
        raise ValueError("Digite a porta usando apenas números.")
    porta = int(texto)
    if not PORTA_MINIMA <= porta <= PORTA_MAXIMA:
        raise ValueError(f"A porta deve estar entre {PORTA_MINIMA} e {PORTA_MAXIMA}.")
    if porta in (PORTA_PAINEL, PORTA_CLIENTE):
        raise ValueError(f"As portas {PORTA_PAINEL} e {PORTA_CLIENTE} são reservadas para o painel e o cliente.")
    if porta_em_uso(porta):
        raise ValueError(f"A porta {porta} já está em uso por outro programa.")
    return porta


class ControleAPI:
    def __init__(self, fabrica_api):
        self._fabrica_api = fabrica_api
        self._trava = threading.Lock()
        self._servidor = None
        self._thread = None
        self._porta = None

    def iniciar(self, valor_porta):
        with self._trava:
            if self._servidor is not None:
                raise ValueError(f"A API já está rodando na porta {self._porta}.")
            porta = validar_porta(valor_porta)
            try:
                servidor = make_server("0.0.0.0", porta, self._fabrica_api(), threaded=True)
            except OSError:
                raise ValueError(f"Não foi possível abrir a porta {porta}.")
            self._thread = threading.Thread(target=servidor.serve_forever, daemon=True)
            self._thread.start()
            self._servidor = servidor
            self._porta = porta
            return porta

    def parar(self):
        with self._trava:
            if self._servidor is None:
                raise ValueError("A API não está rodando.")
            self._servidor.shutdown()
            self._servidor.server_close()
            self._thread.join(timeout=5)
            self._servidor = None
            self._thread = None
            self._porta = None

    def estado(self):
        with self._trava:
            return {"rodando": self._servidor is not None, "porta": self._porta}
