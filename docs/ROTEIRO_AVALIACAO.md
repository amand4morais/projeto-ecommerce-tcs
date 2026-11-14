# Roteiro da avaliação — EP-2

Projeto: Serviço de Reserva de Estoque e Pedidos para E-commerce · Protocolo da turma **1.5.0**

## 1. Antes do dia
- [ ] Último commit enviado ao GitHub e **código-fonte entregue ao professor** (OBS 2).
- [ ] Protocolo da turma entregue (OBS 1) e ainda na versão **1.5.0** no repositório
      github.com/JoseMarra2006/protocolo-cliente-servidor. Se mudou, revisar antes da avaliação.
- [ ] Projeto no pendrive ou acessível pelo GitHub (sem a pasta `.venv`).

## 2. Preparação no laboratório
Na pasta do projeto, pelo PowerShell:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

1. Se existir um `servidor\ecommerce.db` antigo, apagar (começa limpo, com o ADM padrão).
2. **Terminal 1:** `python servidor/main.py` → abrir http://127.0.0.1:5000 → porta (ex.: `8080`) → **Iniciar API**.
   Se o Windows perguntar sobre o Firewall, **permitir**.
3. Passar aos colegas o IP e a porta do quadro **Informe aos clientes**.
4. **Terminal 2** (com a `.venv` ativa): `python cliente/main.py` → abrir http://127.0.0.1:5001.
5. No cliente: IP e porta do servidor a ser testado → **Conectar**.

ADM padrão (igual em todos os servidores): `adm@teste.com` / `admin123`.
**Não alterar nem excluir o ADM padrão durante a avaliação.**

## 3. Onde mostrar o que foi enviado e recebido
| Lado | Onde |
|---|---|
| Cliente | botão **Comunicação** (canto inferior direito): cada requisição enviada e a resposta recebida |
| Servidor | página **Comunicação** do painel: o que chegou e o que foi respondido |
| Servidor (item q) | página **Visão geral** → **Usuários logados** |

## 4. Itens do cliente (a–h)
Preparação: uma conta comum no servidor avaliado (ex.: `maria@exemplo.com` / `Senha123`).

| Item | Login | Onde | O que fazer | Resultado esperado |
|---|---|---|---|---|
| a) ler outros usuários | ADM | **Usuários** | lista abre sozinha; **Ver** na linha da conta comum | dados do usuário no painel ao lado (GET /users/{id} → 200) |
| b) atualizar outros | ADM | **Usuários** | **Editar** → mudar o nome → Salvar | "Usuário atualizado." (PATCH → 200) |
| c) apagar outros | ADM | **Usuários** | **Excluir** em uma conta comum → confirmar | "Usuário excluído." (DELETE → 204) |
| d) cadastrar produto | ADM | **Produtos** | **Novo produto** → nome, descrição, quantidade → Cadastrar | "Produto cadastrado." (POST → 201) |
| e) ler produtos | ADM | **Produtos** | lista abre sozinha; **Consultar** em um produto | estoque em destaque (GET → 200) |
| f) atualizar produto | ADM | **Produtos** | produto consultado → **Editar** → mudar a quantidade → Salvar | "Produto atualizado." (PATCH → 200) |
| g) remover produto | ADM | **Produtos** | produto consultado → **Excluir** → confirmar | "Produto excluído." (DELETE → 204) |
| h) comum consulta estoque | comum | **Produtos** | **Consultar** em um produto | estoque em destaque; sem botões de escrita |


## 5. Itens do servidor (i–q)
O colega usa o cliente dele com o IP e porta. Acompanhar na página **Comunicação** do painel.

| Item | Requisição esperada | Resposta do servidor |
|---|---|---|
| i) enviar dados de outros | GET /users/{id} (ADM) | 200 `{id, nome, email, admin}` |
| j) atualizar outros | PUT ou PATCH /users/{id} (ADM) | 200 com os dados atualizados |
| k) apagar outros | DELETE /users/{id} (ADM) | 204 (e as sessões do usuário são encerradas) |
| l) cadastrar produto | POST /products (ADM) | 201 + `Location: /api/v1/products/{id}` |
| m) ler produtos | GET /products e GET /products/{id} | 200 |
| n) atualizar produto | PUT ou PATCH /products/{id} (ADM) | 200 |
| o) remover produto | DELETE /products/{id} (ADM) | 204 |
| p) comum consulta estoque | GET /products/{id} (comum) | 200 |
| q) usuários logados | — | **Visão geral**: quem entra aparece e quem sai some em até 2 s |

Respostas de erro esperadas (se o professor testar): 401 sem token; 403 para comum em rotas de ADM;
404 para id inexistente (ADM); 400 para dados inválidos (ex.: quantidade `-1`, `1.5` ou texto); 409 para e-mail repetido.
