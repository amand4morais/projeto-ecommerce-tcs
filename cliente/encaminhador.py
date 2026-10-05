import re

import requests

PREFIXO = "/api/v1"
TEMPO_LIMITE = 5
LIMITE_TEXTO = 2000
METODOS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
PADRAO_HOST = re.compile(r"[A-Za-z0-9.-]+")
PADRAO_CAMINHO = re.compile(r"/[A-Za-z0-9/_.%-]*")

sessao_http = requests.Session()
# Ignora proxies configurados no sistema: no laboratório eles bloqueariam o acesso à rede local.
sessao_http.trust_env = False


class ErroEnvio(Exception):
    pass


def validar_host(valor):
    host = valor.strip() if isinstance(valor, str) else ""
    if not PADRAO_HOST.fullmatch(host):
        raise ValueError("Informe um IP válido (ex.: 192.168.0.10).")
    return host


def validar_porta(valor):
    texto = str(valor).strip() if isinstance(valor, (str, int)) and not isinstance(valor, bool) else ""
    if not texto.isdecimal() or not 1 <= int(texto) <= 65535:
        raise ValueError("Informe uma porta entre 1 e 65535.")
    return int(texto)


def validar_metodo(valor):
    if valor not in METODOS:
        raise ValueError("Método HTTP não suportado.")
    return valor


def validar_caminho(valor):
    if not isinstance(valor, str) or not PADRAO_CAMINHO.fullmatch(valor):
        raise ValueError("Caminho da requisição inválido.")
    return valor


def ler_corpo(resposta):
    try:
        return resposta.json(), None
    except ValueError:
        return None, resposta.text[:LIMITE_TEXTO]


def encaminhar(host, porta, metodo, caminho, corpo=None, token=None):
    url = f"http://{host}:{porta}{PREFIXO}{caminho}"
    cabecalhos = {"Authorization": f"Bearer {token}"} if token else {}
    argumentos = {"json": corpo} if corpo is not None else {}
    try:
        resposta = sessao_http.request(metodo, url, headers=cabecalhos, timeout=TEMPO_LIMITE, **argumentos)
    except requests.Timeout:
        raise ErroEnvio(f"O servidor {host}:{porta} não respondeu em {TEMPO_LIMITE} segundos.")
    except requests.ConnectionError:
        raise ErroEnvio(f"Não foi possível conectar a {host}:{porta}. Verifique o IP, a porta e se o servidor está ligado.")
    except requests.RequestException:
        raise ErroEnvio(f"Falha ao enviar a requisição para {host}:{porta}.")
    corpo_json, texto = ler_corpo(resposta)
    return {"url": url, "status": resposta.status_code, "corpo": corpo_json, "texto": texto}
