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

## Execução
_A definir na sub-etapa 2 (servidor e cliente ainda não implementados)._