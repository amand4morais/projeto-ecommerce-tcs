import re

PADRAO_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PADRAO_SENHA = re.compile(r"[a-zA-Z0-9]+")
PADRAO_ID = re.compile(r"[0-9]+")
QUANTIDADE_MAXIMA = 1_000_000


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


def validar_login(dados):
    return {
        "email": validar_email(obter_texto(dados, "email")),
        "senha": validar_senha(obter_texto(dados, "senha")),
    }


def validar_usuario_parcial(dados):
    validadores = {"nome": validar_nome, "email": validar_email, "senha": validar_senha}
    campos = {campo: validar(obter_texto(dados, campo)) for campo, validar in validadores.items() if campo in dados}
    if not campos:
        raise ErroValidacao("Envie ao menos um dos campos: nome, email ou senha.")
    return campos


def validar_id(texto, recurso):
    if not PADRAO_ID.fullmatch(texto):
        raise ErroValidacao(f"O id do {recurso} deve ser um número inteiro.")
    return int(texto)


def validar_id_usuario(texto):
    return validar_id(texto, "usuário")


def validar_id_produto(texto):
    return validar_id(texto, "produto")


def validar_nome_produto(valor):
    nome = valor.strip()
    if not 2 <= len(nome) <= 100:
        raise ErroValidacao("O nome do produto deve ter entre 2 e 100 caracteres.")
    return nome


def validar_descricao(valor):
    descricao = valor.strip()
    if len(descricao) > 500:
        raise ErroValidacao("A descrição deve ter no máximo 500 caracteres.")
    return descricao


def obter_quantidade(dados):
    if "quantidade" not in dados:
        raise ErroValidacao("O campo quantidade é obrigatório.")
    valor = dados["quantidade"]
    # bool é subclasse de int em Python; true/false não são quantidades válidas.
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise ErroValidacao("A quantidade deve ser um número inteiro.")
    if not 0 <= valor <= QUANTIDADE_MAXIMA:
        raise ErroValidacao("A quantidade deve estar entre 0 e 1.000.000.")
    return valor


def validar_produto_completo(dados):
    return {
        "nome": validar_nome_produto(obter_texto(dados, "nome")),
        "descricao": validar_descricao(obter_texto(dados, "descricao")),
        "quantidade": obter_quantidade(dados),
    }


def validar_produto_parcial(dados):
    campos = {}
    if "nome" in dados:
        campos["nome"] = validar_nome_produto(obter_texto(dados, "nome"))
    if "descricao" in dados:
        campos["descricao"] = validar_descricao(obter_texto(dados, "descricao"))
    if "quantidade" in dados:
        campos["quantidade"] = obter_quantidade(dados)
    if not campos:
        raise ErroValidacao("Envie ao menos um dos campos: nome, descricao ou quantidade.")
    return campos
