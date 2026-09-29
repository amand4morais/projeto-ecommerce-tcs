import re

PADRAO_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PADRAO_SENHA = re.compile(r"[a-zA-Z0-9]+")


class ErroValidacao(Exception):
    pass


def ler_objeto_json(requisicao):
    if not requisicao.is_json:
        raise ErroValidacao("O corpo da requisição deve ser JSON (Content-Type: application/json).")
    dados = requisicao.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ErroValidacao("O corpo da requisição deve ser um objeto JSON válido.")
    return dados


def obter_texto(dados, campo):
    if campo not in dados:
        raise ErroValidacao(f"O campo {campo} é obrigatório.")
    valor = dados[campo]
    if not isinstance(valor, str):
        raise ErroValidacao(f"O campo {campo} deve ser um texto.")
    return valor


def validar_nome(valor):
    nome = valor.strip()
    if not 3 <= len(nome) <= 50:
        raise ErroValidacao("O nome deve ter entre 3 e 50 caracteres.")
    return nome


def validar_email(valor):
    if not 5 <= len(valor) <= 30:
        raise ErroValidacao("O e-mail deve ter entre 5 e 30 caracteres.")
    if not PADRAO_EMAIL.fullmatch(valor):
        raise ErroValidacao("O e-mail deve estar no formato nome@dominio.com.")
    return valor


def validar_senha(valor):
    if not 6 <= len(valor) <= 20:
        raise ErroValidacao("A senha deve ter entre 6 e 20 caracteres.")
    if not PADRAO_SENHA.fullmatch(valor):
        raise ErroValidacao("A senha deve conter apenas letras e números.")
    return valor


def validar_usuario_completo(dados):
    return {
        "nome": validar_nome(obter_texto(dados, "nome")),
        "email": validar_email(obter_texto(dados, "email")),
        "senha": validar_senha(obter_texto(dados, "senha")),
    }
