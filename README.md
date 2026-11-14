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
- `servidor/` — API REST + painel web (Visão geral e Comunicação)
- `cliente/` — interface web do cliente (Acesso, Minha conta, Produtos e Usuários)
- `docs/` — relatórios (regras e acompanhamento) e `ROTEIRO_AVALIACAO.md`

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
   O quadro **Informe aos clientes** mostra o IP e a porta (ou consulte com `ipconfig`).

Páginas do painel:
- **Visão geral** — controle da API, indicadores e a lista de **usuários logados** (atualizada a cada 2 s).
- **Comunicação** — cada requisição recebida e a resposta enviada (token mascarado), em visão detalhada ou resumo.
4. Se o Windows perguntar sobre o Firewall, permita o acesso do Python à rede.
5. Para encerrar: **Parar API** no painel e `Ctrl+C` no terminal.

O banco `servidor/ecommerce.db` é criado automaticamente na primeira execução.
Se ele for de uma versão anterior do projeto, a API não inicia e o painel pede para apagá-lo.

### ADM padrão
Sempre que a API inicia, o servidor cria o ADM padrão do protocolo, caso ele ainda não exista:
`Admin` / `adm@teste.com` / `admin123`. Não altere nem remova esse usuário durante a avaliação.

## Execução do cliente
Com o ambiente virtual ativo, na pasta do projeto (em outro terminal, se o servidor também estiver rodando):

```powershell
python cliente/main.py
```

1. Abra http://127.0.0.1:5001 no navegador.
2. Preencha o **IP** e a **porta** do servidor (o próprio ou o de um colega) e clique em **Conectar**.
   Cada servidor tem o próprio banco: para usar o servidor de um colega, crie uma conta nele.
3. O botão **Comunicação** (canto inferior direito) abre a gaveta com cada requisição enviada e a resposta recebida.

Páginas do cliente:
- **Acesso** — conexão (IP, porta, Conectar) e as abas Entrar / Criar conta.
- **Minha conta** — dados carregados automaticamente, edição e exclusão da própria conta.
- **Produtos** — consulta do estoque para todos; cadastro, edição e exclusão para o ADM.
- **Usuários** — só para o ADM: ler, editar e excluir o cadastro de outros usuários.

## Avaliação
Veja `docs/ROTEIRO_AVALIACAO.md` (preparação no laboratório, item por item e checklist).

## Testes automatizados
Na pasta do projeto, com o ambiente virtual ativo:

```powershell
python -m unittest discover -s servidor -v
python -m unittest discover -s cliente -v
```
