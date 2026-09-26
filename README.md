# Projeto Final — Serviço de Reserva de Estoque e Pedidos para E-commerce

Projeto da disciplina Tecnologias Cliente-Servidor (TADS — UTFPR Ponta Grossa).
Cliente e servidor se comunicam via HTTP/JSON (REST nível 2), seguindo o
protocolo da turma: https://github.com/JoseMarra2006/protocolo-cliente-servidor

## Tecnologias
- Python 3.9 ou superior (desenvolvido com 3.14.3)
- Flask (servidor e interface web do cliente)
- requests (cliente → servidores)
- SQLite (módulo `sqlite3`, já incluso no Python)

## Estrutura
- `servidor/` — API REST + painel web para escolher a porta
- `cliente/` — interface web do cliente
- `docs/` — documento de regras e documento de acompanhamento

## Instalação (Windows / PowerShell)
Na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (uma única vez).

## Execução do servidor
Com o ambiente virtual ativo, na pasta do projeto:

```powershell
python servidor/main.py
```

1. Abra http://127.0.0.1:5000 no navegador (painel, acessível só nesta máquina).
2. Digite a porta da API (1024 a 65535, exceto 5000 e 5001) e clique em **Iniciar API**.
3. A API fica disponível em `http://<IP desta máquina>:<porta>/api/v1` para toda a rede.
   O IP pode ser consultado com `ipconfig` (campo "Endereço IPv4").
4. Se o Windows perguntar sobre o Firewall, permita o acesso do Python à rede.
5. Para encerrar: **Parar API** no painel e `Ctrl+C` no terminal.

O banco `servidor/ecommerce.db` é criado automaticamente na primeira execução.

## Execução do cliente
_A definir (sub-etapa 5)._

## Testes automatizados
Na pasta do projeto, com o ambiente virtual ativo:

```powershell
python -m unittest discover -s servidor -v
```
