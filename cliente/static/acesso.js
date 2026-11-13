const campoHost = document.getElementById("host");
const campoPorta = document.getElementById("porta");
const botaoConectar = document.getElementById("botao-conectar");
const botaoDesconectar = document.getElementById("botao-desconectar");
const estadoConexao = document.getElementById("estado-conexao");
const avisoConexao = document.getElementById("aviso-conexao");
const telaVisitante = document.getElementById("tela-visitante");
const abaEntrar = document.getElementById("aba-entrar");
const abaCadastro = document.getElementById("aba-cadastro");
const formEntrar = document.getElementById("form-entrar");
const formCadastro = document.getElementById("form-cadastro");

function selecionarAba(aba) {
  const entrar = aba === "entrar";
  abaEntrar.setAttribute("aria-selected", String(entrar));
  abaCadastro.setAttribute("aria-selected", String(!entrar));
  formEntrar.hidden = !entrar;
  formCadastro.hidden = entrar;
}

function exibirConexao() {
  const conexao = obterConexao();
  const conectado = Boolean(conexao);
  campoHost.disabled = conectado;
  campoPorta.disabled = conectado;
  botaoConectar.hidden = conectado;
  botaoDesconectar.hidden = !conectado;
  estadoConexao.textContent = conectado ? "Conectado" : "Desconectado";
  estadoConexao.dataset.conectado = String(conectado);
  avisoConexao.hidden = conectado;
  telaVisitante.hidden = !conectado;
  if (conectado) {
    campoHost.value = conexao.host;
    campoPorta.value = conexao.porta;
  }
  exibirIdentidade();
}

async function conectar() {
  const destino = { host: campoHost.value.trim(), porta: campoPorta.value.trim() };
  const resposta = await enviarRequisicao("OPTIONS", "/users", undefined, false, destino);
  if (resposta.status === null) {
    mostrarMensagem(resposta.mensagem, "erro");
    return;
  }
  salvarConexao(destino);
  exibirConexao();
  if (resposta.ok) {
    mostrarMensagem("Servidor encontrado. Agora você pode entrar ou criar uma conta.", "sucesso");
  } else {
    mostrarMensagem(`O servidor respondeu, mas com status ${resposta.status} ao teste de conexão. Ele pode não seguir o protocolo.`, "erro");
  }
}

function desconectar() {
  limparConexao();
  exibirConexao();
  mostrarMensagem("");
}

async function criarConta(evento) {
  evento.preventDefault();
  const corpo = lerCampos(formCadastro, ["nome", "email", "senha"]);
  const resposta = await enviarRequisicao("POST", "/users", corpo);
  if (!resposta.ok) {
    mostrarMensagem(resposta.mensagem, "erro");
    return;
  }
  formCadastro.reset();
  selecionarAba("entrar");
  formEntrar.elements.email.value = corpo.email;
  mostrarMensagem("Conta criada! Agora é só entrar.", "sucesso");
}

async function entrar(evento) {
  evento.preventDefault();
  const corpo = lerCampos(formEntrar, ["email", "senha"]);
  const resposta = await enviarRequisicao("POST", "/sessions", corpo);
  if (!resposta.ok) {
    mostrarMensagem(resposta.mensagem, "erro");
    return;
  }
  const dados = resposta.corpo;
  if (!dados || typeof dados.token !== "string" || dados.id === undefined || dados.id === null) {
    mostrarMensagem("O servidor respondeu ao login sem o id da sessão ou o token.", "erro");
    return;
  }
  const usuario = dados.usuario && typeof dados.usuario === "object" ? dados.usuario : { email: corpo.email };
  salvarSessao({
    id: String(dados.id),
    token: dados.token,
    usuario: { ...usuario, admin: usuario.admin === true },
    host: obterConexao().host,
    porta: obterConexao().porta,
  });
  irPara("/conta", `Bem-vindo(a), ${usuario.nome ?? corpo.email}!`);
}

abaEntrar.addEventListener("click", () => { selecionarAba("entrar"); mostrarMensagem(""); });
abaCadastro.addEventListener("click", () => { selecionarAba("cadastro"); mostrarMensagem(""); });
formCadastro.addEventListener("submit", (e) => comBotaoOcupado(e.submitter ?? formCadastro.querySelector("button"), () => criarConta(e)));
formEntrar.addEventListener("submit", (e) => comBotaoOcupado(e.submitter ?? formEntrar.querySelector("button"), () => entrar(e)));
botaoConectar.addEventListener("click", () => comBotaoOcupado(botaoConectar, conectar));
botaoDesconectar.addEventListener("click", desconectar);
for (const campo of [campoHost, campoPorta]) {
  campo.addEventListener("keydown", (e) => { if (e.key === "Enter" && !botaoConectar.disabled) botaoConectar.click(); });
}

if (paginaLiberada) exibirConexao();
